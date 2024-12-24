import boto3
import os
import json
import uuid
from utils.cors_utils import build_response

# Initialize S3 client
s3 = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        file_name = body.get('fileName', '')
        content_type = body.get('contentType')

        if not content_type:
            raise ValueError("Content-Type is required")

        # Supported audio extensions map
        extensions_map = {
            'audio/mpeg': '.mp3',
            'audio/flac': '.flac',
            'audio/x-wav': '.wav',
            'audio/aac': '.aac'
        }

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
            ExpiresIn=600  # URL valid for 10 minutes
        )

        return build_response(200, json.dumps({
            "presignedUrl": presigned_url,
            "trackId": track_id,
            "s3Key": s3_key,
            "fileName": file_name
        }))
    except ValueError as ve:
        return build_response(400, json.dumps({"error": str(ve)}))
    except Exception as e:
        return build_response(500, json.dumps({"error": str(e)}))