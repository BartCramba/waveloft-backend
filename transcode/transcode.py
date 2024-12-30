import json
import os
import subprocess
import boto3
import urllib.parse

DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']  # e.g. "Tracks"
BUCKET_NAME = os.environ['BUCKET_NAME']        # e.g. "wave-loft-audio-bucket"

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)
s3 = boto3.client('s3')

def flac_to_mp3_handler(event, context):
    """
    Triggered by S3 PutObject for *.flac in 'flac/' prefix.

    We'll:
      1) Download the FLAC file to /tmp
      2) Run ffmpeg => produce /tmp/output.mp3 (320 kbps)
      3) Upload MP3 to S3 -> 'mp3/' prefix
      4) Using the object metadata (trackId), we update that DB item so audioS3Key = "mp3/..."
    """
    print("==== Received S3 Event ====")
    print(json.dumps(event, indent=2))

    # Each record is an S3 event
    records = event.get('Records', [])
    for record in records:
        bucket = record['s3']['bucket']['name']
        raw_key = record['s3']['object']['key']
        size_bytes = record['s3']['object'].get('size', 0)

        # decode any URL-encoded chars like spaces
        key = urllib.parse.unquote_plus(raw_key)

        # We only transcode .flac files in the "flac/" prefix
        if not key.lower().endswith('.flac') or not key.startswith('flac/'):
            print(f"Skipping object {key} (not in 'flac/' prefix or not .flac).")
            continue

        print(f"Processing FLAC file: {bucket}/{key}, size={size_bytes} bytes")

        # Attempt to read the object's user metadata to get trackId
        try:
            head_resp = s3.head_object(Bucket=bucket, Key=key)
            user_meta = head_resp.get('Metadata', {})
            track_id = user_meta.get('trackid')  # case-insensitive, but best to keep lower
        except Exception as e:
            print(f"ERROR: Could not head_object or read metadata for {key}: {e}")
            track_id = None

        if not track_id:
            print("WARNING: No trackId metadata found. We can't do direct DB update. We'll skip DB update.")
        else:
            print(f"Found trackId={track_id} in object metadata.")

        # local paths
        local_flac_path = '/tmp/source.flac'
        local_mp3_path  = '/tmp/output.mp3'

        # Step 1) Download FLAC
        print(f"Downloading s3://{bucket}/{key} -> {local_flac_path}")
        try:
            s3.download_file(bucket, key, local_flac_path)
        except Exception as e:
            print(f"ERROR: S3 download failed for {key}: {e}")
            continue

        # Step 2) Transcode with ffmpeg => 320 kbps MP3
        cmd = [
            '/opt/ffmpeg',  # or 'ffmpeg' if baked into the Lambda environment
            '-y',
            '-i', local_flac_path,
            '-vn',
            '-ar', '44100',
            '-ac', '2',
            '-b:a', '320k',
            local_mp3_path
        ]
        print(f"Running FFmpeg command: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg failed for {key}: {e}")
            continue

        # Step 3) Upload to mp3/
        mp3_key = key.replace('flac/', 'mp3/').replace('.flac', '.mp3')
        print(f"Uploading MP3 to s3://{bucket}/{mp3_key}")
        try:
            s3.upload_file(local_mp3_path, bucket, mp3_key)
        except Exception as e:
            print(f"ERROR: S3 upload for MP3 failed: {e}")
            continue

        # Step 4) Update DynamoDB if we have trackId
        if track_id:
            print(f"Updating DynamoDB table {DYNAMODB_TABLE} item id={track_id} to {mp3_key}")
            try:
                # We'll do a direct update if item exists
                update_resp = table.update_item(
                    Key={'id': track_id},
                    UpdateExpression="SET audioS3Key = :mp3k",
                    ExpressionAttributeValues={":mp3k": mp3_key},
                    ConditionExpression="attribute_exists(id)"
                )
                print(f"DB update success. Updated item to reference {mp3_key}.")
            except Exception as e:
                print(f"WARNING: Could not update DB for track_id={track_id} => {e}")
        else:
            print("Skipping DB update since no trackId found.")

        # Step 5) Cleanup
        try:
            os.remove(local_flac_path)
            os.remove(local_mp3_path)
        except Exception as e:
            print(f"Warning: error removing local temp files: {e}")

    return {"statusCode": 200, "body": "Transcode done"}
