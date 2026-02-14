import boto3
import os
import json
import uuid
from cors_utils import build_response

# Initialize S3 client
s3 = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        files = body.get('files', [])

        # Ensure files is always a list (even for single file uploads)
        if isinstance(files, dict):  # If a single file is sent as an object
            files = [files]

        if not files or not isinstance(files, list):
            raise ValueError("A list of files is required")

        # Supported audio extensions map
        extensions_map = {
            'audio/mpeg': '.mp3',
            'audio/flac': '.flac',
            'audio/x-wav': '.wav',
            'audio/aac': '.aac'
        }

        presigned_urls = []
        for file in files:
            file_name = file.get('fileName', '')
            content_type = file.get('contentType')

            if not content_type:
                raise ValueError("Content-Type is required for each file")

            if content_type not in extensions_map:
                raise ValueError(f"Unsupported Content-Type: {content_type}")

            # Generate file extension
            file_extension = extensions_map[content_type]

            # Generate unique track ID and S3 key
            track_id = str(uuid.uuid4())
            s3_key = f"tracks/{track_id}{file_extension}"

            # Generate presigned URL for upload
            presigned_url = s3.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': BUCKET_NAME,
                    'Key': s3_key,
                    'ContentType': content_type
                },
                ExpiresIn=7200  # URL valid for 60 minutes
            )

            presigned_urls.append({
                "presignedUrl": presigned_url,
                "trackId": track_id,
                "s3Key": s3_key,
                "fileName": file_name
            })

        return build_response(200, json.dumps({"presignedUrls": presigned_urls}))
    except ValueError as ve:
        return build_response(400, json.dumps({"error": str(ve)}))
    except Exception as e:
        return build_response(500, json.dumps({"error": str(e)}))