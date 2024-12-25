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

# AWS Resources
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment Variables
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
AUDIO_BUCKET = os.environ['S3_BUCKET']
DEFAULT_ALBUM_ART_S3_KEY = "album_art/default_album_art.png"

def lambda_handler(event, context):
    try:
        print("Lambda function started")
        body = json.loads(event['body'])
        files = body['files']
        print(f"Processing {len(files)} files")

        responses = []
        for file_data in files:
            file_name = file_data['fileName']
            audio_s3_key = file_data['s3Key']
            print(f"Processing file: {file_name}, S3 Key: {audio_s3_key}")

            metadata = process_audio_file(file_name, audio_s3_key)
            responses.append(metadata)

        save_metadata_to_dynamodb_batch(responses)
        print("All files processed successfully.")
        return build_response(200, json.dumps({"message": "Tracks created successfully", "tracks": responses}))
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return build_response(500, json.dumps({"error": str(e)}))


def process_audio_file(file_name, audio_s3_key):
    """
    Process an individual audio file: download, extract metadata, and upload album art.
    """
    try:
        # Download the audio file
        print(f"Downloading file from S3: Bucket={AUDIO_BUCKET}, Key={audio_s3_key}")
        local_audio_path = download_file_from_s3(audio_s3_key)
        print(f"File downloaded to: {local_audio_path}")

        # Extract metadata
        print(f"Extracting metadata for file: {local_audio_path}")
        metadata = extract_audio_metadata(local_audio_path, file_name)
        print(f"Extracted metadata: {metadata}")

        # Upload album art
        print(f"Analyzing file for album art: {local_audio_path}")
        album_art_s3_key = upload_album_art(local_audio_path, file_name)

        # Add metadata fields
        metadata.update({
            "id": str(uuid.uuid4()),
            "fileName": file_name,
            "audioS3Key": audio_s3_key,
            "albumArtS3Key": album_art_s3_key,
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
        })
        return metadata

    except Exception as e:
        print(f"Error processing file {file_name}: {e}")
        raise



def extract_audio_metadata(file_path, file_name):
    try:
        print(f"Extracting metadata for file: {file_path}")
        audio = File(file_path, easy=True)
        metadata = {
            "title": audio.get("title", [file_name])[0],
            "artist": audio.get("artist", ["Unknown Artist"])[0],
            "album": audio.get("album", ["Unknown Album"])[0],
        }
        print(f"Extracted metadata: {metadata}")
        return metadata
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return {
            "title": file_name,
            "artist": "Unknown Artist",
            "album": "Unknown Album"
        }


def download_file_from_s3(s3_key):
    local_path = f"/tmp/{uuid.uuid4()}"
    try:
        print(f"Downloading file from S3: Bucket={AUDIO_BUCKET}, Key={s3_key}")
        s3.download_file(AUDIO_BUCKET, s3_key, local_path)
        print(f"File downloaded to: {local_path}")
        return local_path
    except Exception as e:
        print(f"Error downloading file from S3: {e}")
        raise


def upload_album_art(file_path, original_file_name):
    """
    Extract and upload album art for MP3 and FLAC files based on the original file name.
    """
    try:
        album_art_data = None
        file_extension = "jpg"  # Default to jpg if not explicitly provided

        print(f"Analyzing file for album art: {file_path} (Original file: {original_file_name})")

        # Use the original file name to determine the file type
        if original_file_name.lower().endswith('.mp3'):
            print("Detected MP3 file. Attempting to extract album art.")
            audio = MP3(file_path, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    album_art_data = tag.data
                    file_extension = "jpg"
                    print("Album art found in MP3 file.")
                    break

        elif original_file_name.lower().endswith('.flac'):
            print("Detected FLAC file. Attempting to extract album art.")
            audio = FLAC(file_path)
            if hasattr(audio, "pictures") and audio.pictures:
                print(f"FLAC pictures found: {len(audio.pictures)}")
                for picture in audio.pictures:
                    print(f"Picture MIME type: {picture.mime}, Size: {len(picture.data)} bytes")
                    album_art_data = picture.data
                    file_extension = picture.mime.split("/")[-1]
                    break
            else:
                print("No FLAC album art pictures found.")

        else:
            print("Unsupported file type for album art extraction.")
            return DEFAULT_ALBUM_ART_S3_KEY

        # No album art found
        if not album_art_data:
            print("No album art data found in the file. Using default album art.")
            return DEFAULT_ALBUM_ART_S3_KEY

        # Save the album art to a temporary file
        unique_id = str(uuid.uuid4())
        album_art_path = f"/tmp/{unique_id}_album_art.{file_extension}"
        with open(album_art_path, 'wb') as img:
            img.write(album_art_data)
        print(f"Album art saved locally: {album_art_path}")

        # Upload album art to S3
        album_art_s3_key = f"album_art/{os.path.basename(album_art_path)}"
        s3.upload_file(album_art_path, AUDIO_BUCKET, album_art_s3_key)
        print(f"Album art uploaded to S3 with key: {album_art_s3_key}")

        return album_art_s3_key

    except Exception as e:
        print(f"Error during album art extraction or upload: {e}")
        return DEFAULT_ALBUM_ART_S3_KEY



def save_metadata_to_dynamodb_batch(metadata_list):
    table = dynamodb.Table(DYNAMODB_TABLE)
    try:
        print("Saving metadata batch to DynamoDB...")
        with table.batch_writer() as batch:
            for metadata in metadata_list:
                print(f"Saving metadata: {metadata}")
                batch.put_item(Item=metadata)
        print("Metadata batch saved successfully.")
    except Exception as e:
        print(f"Error saving metadata batch to DynamoDB: {e}")
        raise
