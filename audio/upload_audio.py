import boto3
import json
import uuid
from mimetypes import guess_extension
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
BUCKET_NAME = 'wave-loft-audio-bucket'  # Update with your bucket name

def lambda_handler(event, context):
    try:
        body = event["body"]
        content_type = event["headers"].get("Content-Type", "")

        if content_type.startswith("multipart/form-data"):
            # Extract file data
            file_content = event["body"]

            # Determine file extension dynamically
            file_extension = guess_extension(content_type.split(";")[0].strip())
            if not file_extension:
                file_extension = ".bin"  # Default fallback for unknown types

            # Generate a unique filename with the correct extension
            file_name = f"{str(uuid.uuid4())}{file_extension}"

            # Upload to S3
            s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=file_content, ContentType=content_type)

            file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}"

            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Upload successful", "url": file_url}),
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                },
            }

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid content type"}),
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                },
            }

    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {
                "Access-Control-Allow-Origin": "*",
            },
        }