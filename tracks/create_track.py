import boto3
import os
import json
import uuid
from mutagen import File
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from datetime import datetime, timezone
from utils.cors_utils import build_response

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment Variables
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']  # e.g. "Tracks"
AUDIO_BUCKET = os.environ['S3_BUCKET']         # e.g. "wave-loft-audio-bucket"
DEFAULT_ALBUM_ART_S3_KEY = "album_art/default_album_art.png"


def lambda_handler(event, context):
    """
    AWS Lambda, triggered by POST /tracks from API Gateway.

    Expected JSON body, for example:
    {
      "files": [
        {
          "trackId": "abc123-... (UUID from front end)",
          "fileName": "MySong.flac",
          "s3Key": "flac/MySong.flac"
        },
        ...
      ]
    }

    Steps:
      1) Parse the request body for "files".
      2) For each file, do:
         - Download from S3 to /tmp
         - Extract audio metadata (title, artist, album) using `mutagen`.
         - Attempt to extract album art -> upload to S3 or use default.
         - Build a metadata dict (including `id = trackId` from front end).
      3) Batch-write the items to DynamoDB.
      4) Return success JSON with all track metadata.
    """
    try:
        print("Lambda function started")
        body = json.loads(event['body'])
        files = body['files']
        print(f"Processing {len(files)} files")

        responses = []  # accumulate metadata for each file

        # Process each file one by one
        for file_data in files:
            # Attempt to read the trackId from the request
            if 'trackId' not in file_data:
                raise ValueError("Missing 'trackId' in the file_data object")

            track_id = file_data['trackId']
            file_name = file_data['fileName']
            audio_s3_key = file_data['s3Key']
            print(f"\n[create_track] Handling fileName={file_name}, s3Key={audio_s3_key}, trackId={track_id}")

            # Actually process & extract
            metadata = process_audio_file(track_id, file_name, audio_s3_key)
            responses.append(metadata)

        # Finally, do a single batch write to DynamoDB
        save_metadata_to_dynamodb_batch(responses)
        print("All files processed & saved to DynamoDB successfully.")

        # Return success
        return build_response(200, json.dumps({
            "message": "Tracks created successfully",
            "tracks": responses
        }))

    except Exception as e:
        print(f"[create_track] ERROR: {str(e)}")
        return build_response(500, json.dumps({"error": str(e)}))


def process_audio_file(track_id, file_name, audio_s3_key):
    """
    1) Download from S3 -> /tmp
    2) Extract metadata with mutagen
    3) Extract & upload album art if present
    4) Return a dict with 'id' = track_id + all other fields
    """
    local_audio_path = None
    try:
        # Step 1: Download
        local_audio_path = download_file_from_s3(audio_s3_key)

        # Step 2: Extract metadata
        extracted = extract_audio_metadata(local_audio_path, file_name)

        # Step 3: Extract & upload album art
        album_art_s3_key = upload_album_art(local_audio_path, file_name)

        # Build final object
        full_metadata = {
            "id": track_id,  # <-- critical: use same trackId from front-end
            "fileName": file_name,
            "audioS3Key": audio_s3_key,
            "albumArtS3Key": album_art_s3_key,
            "title": extracted["title"],
            "artist": extracted["artist"],
            "album": extracted["album"],
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
        }

        print(f"File {file_name} -> full_metadata: {json.dumps(full_metadata, indent=2)}")
        return full_metadata

    except Exception as e:
        print(f"[process_audio_file] Error: {e}")
        raise

    finally:
        # Clean up local file
        if local_audio_path and os.path.exists(local_audio_path):
            try:
                os.remove(local_audio_path)
                print(f"Removed temp audio file: {local_audio_path}")
            except Exception as cleanupErr:
                print(f"Error removing local file: {cleanupErr}")


def download_file_from_s3(s3_key):
    """Download the file from S3 to a random /tmp path and return that path."""
    local_path = os.path.join("/tmp", str(uuid.uuid4()))
    print(f"Downloading: Bucket={AUDIO_BUCKET}, Key={s3_key} => {local_path}")
    s3.download_file(AUDIO_BUCKET, s3_key, local_path)
    print(f"Download complete: {local_path}")
    return local_path


def extract_audio_metadata(file_path, fallback_name):
    """
    Use mutagen to read basic info: title, artist, album.
    If any step fails or is missing, fallback to the file name as title, 'Unknown Artist', etc.
    """
    try:
        audio = File(file_path, easy=True)
        result = {
            "title": audio.get("title", [fallback_name])[0],
            "artist": audio.get("artist", ["Unknown Artist"])[0],
            "album": audio.get("album", ["Unknown Album"])[0],
        }
        print(f"Extracted audio metadata from {file_path}: {result}")
        return result
    except Exception as e:
        print(f"extract_audio_metadata error: {e}")
        return {
            "title": fallback_name,
            "artist": "Unknown Artist",
            "album": "Unknown Album"
        }


def upload_album_art(file_path, original_file_name):
    """
    Attempt to extract embedded album art using Mutagen.
    If found, upload to S3 => return album_art/key
    Else return DEFAULT_ALBUM_ART_S3_KEY
    """
    try:
        album_art_data = None
        file_ext = "jpg"

        # If MP3
        if original_file_name.lower().endswith(".mp3"):
            audio = MP3(file_path, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    album_art_data = tag.data
                    file_ext = "jpg"
                    break

        # If FLAC
        elif original_file_name.lower().endswith(".flac"):
            audio = FLAC(file_path)
            if hasattr(audio, "pictures") and audio.pictures:
                for pic in audio.pictures:
                    album_art_data = pic.data
                    if pic.mime and "/" in pic.mime:
                        file_ext = pic.mime.split("/")[-1] or "jpg"
                    break

        if not album_art_data:
            print("No embedded album art found, returning default.")
            return DEFAULT_ALBUM_ART_S3_KEY

        # Write album art to /tmp
        unique_id = str(uuid.uuid4())
        album_art_path = f"/tmp/{unique_id}_album_art.{file_ext}"
        with open(album_art_path, "wb") as f:
            f.write(album_art_data)

        # Upload to S3
        album_art_s3_key = f"album_art/{os.path.basename(album_art_path)}"
        print(f"Uploading album art => {AUDIO_BUCKET}/{album_art_s3_key}")
        s3.upload_file(album_art_path, AUDIO_BUCKET, album_art_s3_key)

        # Cleanup
        try:
            os.remove(album_art_path)
        except Exception as e:
            print(f"Error removing temp album art file: {e}")

        return album_art_s3_key

    except Exception as e:
        print(f"upload_album_art error: {e}")
        return DEFAULT_ALBUM_ART_S3_KEY


def save_metadata_to_dynamodb_batch(metadata_list):
    """
    Write the final track items to DynamoDB in a single batch.
    Each item is dict with 'id' = trackId from the front-end, etc.
    """
    table = dynamodb.Table(DYNAMODB_TABLE)
    try:
        print(f"Saving {len(metadata_list)} tracks to DynamoDB table {DYNAMODB_TABLE} via batch_writer...")
        with table.batch_writer() as batch:
            for item in metadata_list:
                print(f"batch.put_item => {item}")
                batch.put_item(Item=item)
        print("DynamoDB batch write completed.")
    except Exception as e:
        print(f"save_metadata_to_dynamodb_batch error: {e}")
        raise
