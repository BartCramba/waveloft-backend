import boto3
import os
import json
import uuid
import tempfile
from mutagen import File
from mutagen.flac import FLAC
from datetime import datetime, UTC
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from utils.cors_utils import build_response

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment variables
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
AUDIO_BUCKET = os.environ['S3_BUCKET']
DEFAULT_ALBUM_ART_S3_KEY = "album_art/default_album_art.png"  # S3 key for default album art

def lambda_handler(event, context):
    try:
        print("Lambda function started")

        # Parse the incoming request
        print(f"Received event: {json.dumps(event)}")
        body = json.loads(event['body'])
        file_name = body['fileName']
        audio_s3_key = body['s3Key']
        print(f"Processing file: {file_name}, S3 Key: {audio_s3_key}")

        # Process the audio file
        metadata = process_audio_file(file_name, audio_s3_key)
        print(f"Metadata extracted: {json.dumps(metadata)}")

        # Save metadata to DynamoDB
        save_metadata_to_dynamodb(metadata)
        print("Metadata successfully saved to DynamoDB.")

        # Respond with success
        return build_response(200, json.dumps({"message": "Track created successfully", "metadata": metadata}))
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return build_response(500, json.dumps({"error": str(e)}))

def process_audio_file(file_name, audio_s3_key):
    """
    Process the audio file: download, extract metadata, and upload album art.
    """
    # Download audio file from S3
    local_audio_path = download_file_from_s3(audio_s3_key)

    # Detect file type explicitly and extract metadata
    print(f"Detecting file type for: {file_name}")
    if file_name.lower().endswith('.mp3'):
        file_type = 'mp3'
        audio = MP3(local_audio_path, ID3=ID3)
        print("MP3 file detected.")
    elif file_name.lower().endswith('.flac'):
        file_type = 'flac'
        audio = FLAC(local_audio_path)
        print("FLAC file detected.")
    else:
        file_type = 'unknown'
        audio = File(local_audio_path, easy=True)
        print("Unknown or generic audio file detected.")

    if not audio:
        raise ValueError(f"Unsupported or invalid audio file: {file_name}")

    print(f"Extracting metadata for: {file_name}")
    metadata = extract_audio_metadata(audio, file_name)
    print(f"Extracted metadata: {json.dumps(metadata)}")

    # Upload album art, passing the determined file type
    print("Checking for album art...")
    album_art_s3_key = upload_album_art(local_audio_path, AUDIO_BUCKET, "album_art", file_type)
    if album_art_s3_key:
        print(f"Album art uploaded: {album_art_s3_key}")
        metadata['albumArtUrl'] = generate_presigned_url(album_art_s3_key)

    # Add additional metadata
    metadata.update({
        "id": str(uuid.uuid4()),
        "fileName": file_name,
        "audioS3Key": audio_s3_key,
        "albumArtS3Key": album_art_s3_key,  # Optional field for album art
        "uploadedAt": datetime.now(UTC).isoformat()
    })

    print(f"Final metadata: {json.dumps(metadata)}")
    return metadata


def extract_audio_metadata(audio, file_name):
    """
    Extract audio metadata using Mutagen.
    """
    title = audio.get("title", [file_name])[0]
    title = title.replace(".mp3", "").strip()  # Remove file extension
    artist = audio.get("artist", ["Unknown Artist"])[0]

    # Infer artist from title if missing
    if artist == "Unknown Artist" and "-" in title:
        artist, title = map(str.strip, title.split("-", 1))

    return {
        "title": title,
        "artist": artist,
        "album": audio.get("album", ["Unknown Album"])[0],
        "duration": int(audio.info.length) if hasattr(audio, 'info') else 0,
        "bitrate": getattr(audio.info, 'bitrate', None) // 1000 if hasattr(audio, 'info') else None
    }

def download_file_from_s3(s3_key):
    local_path = f"/tmp/{uuid.uuid4()}"
    print(f"Downloading file from S3. Bucket: {AUDIO_BUCKET}, Key: {s3_key}")
    s3.download_file(AUDIO_BUCKET, s3_key, local_path)
    print(f"File downloaded to: {local_path}")
    return local_path

def upload_album_art(file_path, s3_bucket, s3_key_prefix, file_type):
    """
    Extract and upload album art from audio files (MP3/FLAC) with the file type passed in.
    """
    album_art_path = None

    try:
        print(f"File path: {file_path}")
        print(f"Received file type: {file_type}")

        # Use a unique identifier for the album art filename
        unique_id = str(uuid.uuid4())

        if file_type == 'mp3':
            print("Attempting to process MP3 file for album art.")
            audio = MP3(file_path, ID3=ID3)
            print(f"MP3 tags: {audio.tags.values()}")  # Debugging the tags

            for tag in audio.tags.values():
                print(f"Checking tag: {tag}")
                if isinstance(tag, APIC):  # MP3 album art
                    album_art_path = f'/tmp/{unique_id}_album_art.jpg'
                    with open(album_art_path, 'wb') as img:
                        img.write(tag.data)
                    print(f"MP3 album art extracted and saved to: {album_art_path}")
                    break
        elif file_type == 'flac':
            print("Attempting to process FLAC file for album art.")
            audio = FLAC(file_path)
            print(f"FLAC pictures: {audio.pictures}")  # Debugging the pictures

            for picture in audio.pictures:
                print(f"Checking picture: {picture}")
                album_art_path = f"/tmp/{unique_id}_album_art.{picture.mime.split('/')[-1]}"
                with open(album_art_path, 'wb') as img:
                    img.write(picture.data)
                print(f"FLAC album art extracted and saved to: {album_art_path}")
                break

        if not album_art_path:
            print("No album art found in the audio file. Using default album art.")
            return DEFAULT_ALBUM_ART_S3_KEY

        # Upload the album art to S3
        album_art_s3_key = f"{s3_key_prefix}/{os.path.basename(album_art_path)}"
        print(f"Prepared S3 key for album art: {album_art_s3_key}")
        s3.upload_file(album_art_path, s3_bucket, album_art_s3_key)
        print(f"Album art successfully uploaded to S3: {album_art_s3_key}")

        return album_art_s3_key
    except Exception as e:
        print(f"Error during album art extraction or upload: {e}")
        return DEFAULT_ALBUM_ART_S3_KEY


def upload_picture_to_s3(picture_data, mime_type):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as album_art_temp_file:
            album_art_temp_file.write(picture_data)
            album_art_temp_file.flush()

            album_art_s3_key = f"album_art/{uuid.uuid4()}.jpg"
            print(f"Uploading album art to S3: {album_art_s3_key}")
            s3.upload_file(
                album_art_temp_file.name,
                AUDIO_BUCKET,
                album_art_s3_key,
                ExtraArgs={"ContentType": mime_type}
            )
            print(f"Album art uploaded to S3: {album_art_s3_key}")
            return album_art_s3_key
    except Exception as e:
        print(f"Error saving album art to S3: {str(e)}")
        return None

def generate_presigned_url(s3_key):
    """
    Generate a presigned URL for a given S3 key.
    """
    try:
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': AUDIO_BUCKET, 'Key': s3_key},
            ExpiresIn=3600  # URL valid for 1 hour
        )
        print(f"Generated presigned URL for S3 Key: {s3_key}")
        return presigned_url
    except Exception as e:
        print(f"Error generating presigned URL: {str(e)}")
        return None

def save_metadata_to_dynamodb(metadata):
    try:
        print(f"Saving metadata to DynamoDB: {json.dumps(metadata)}")
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.put_item(Item=metadata)
        print("Metadata saved to DynamoDB successfully.")
    except Exception as e:
        print(f"Error saving metadata to DynamoDB: {str(e)}")
        raise
