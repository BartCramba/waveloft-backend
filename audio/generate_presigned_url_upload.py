import boto3
import os
import json
import uuid
from cors_utils import build_response

s3 = boto3.client("s3")
BUCKET_NAME = os.environ["BUCKET_NAME"]

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        files = body.get("files", [])

        # Allow single object
        if isinstance(files, dict):
            files = [files]

        if not files or not isinstance(files, list):
            return build_response(400, {"error": "A list of files is required"})

        extensions_map = {
            "audio/mpeg": ".mp3",
            "audio/flac": ".flac",
            "audio/x-wav": ".wav",
            "audio/aac": ".aac",
        }

        presigned_urls = []
        for f in files:
            file_name = f.get("fileName", "")
            content_type = f.get("contentType")

            if not content_type:
                return build_response(400, {"error": "Content-Type is required for each file"})

            if content_type not in extensions_map:
                return build_response(400, {"error": f"Unsupported Content-Type: {content_type}"})

            file_extension = extensions_map[content_type]
            track_id = str(uuid.uuid4())

            # NOTE: This is your upload flow; leaving it unchanged.
            s3_key = f"tracks/{track_id}{file_extension}"

            presigned_url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=7200,  # 2 hours
            )

            presigned_urls.append({
                "presignedUrl": presigned_url,
                "trackId": track_id,
                "s3Key": s3_key,
                "fileName": file_name,
            })

        # IMPORTANT: build_response already JSON-encodes. Pass a dict, not json.dumps(...)
        return build_response(200, {"presignedUrls": presigned_urls})

    except ValueError as ve:
        return build_response(400, {"error": str(ve)})
    except Exception as e:
        return build_response(500, {"error": str(e)})
