import boto3
import os
import json
from decimal import Decimal

from botocore.config import Config
from botocore.exceptions import ClientError
from utils.cors_utils import build_response

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb')
my_config = Config(
    region_name="eu-north-1",
    signature_version="s3v4",
    s3={'addressing_style': 'virtual'}  # or 'path'
)

s3 = boto3.client(
    "s3",
    config=my_config,
    endpoint_url="https://s3.eu-north-1.amazonaws.com"
)

# Environment variables
TABLE_NAME = os.environ['DYNAMODB_TABLE']
BUCKET_NAME = os.environ['BUCKET_NAME']

# Custom JSON Encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Convert Decimal to float for JSON serialization
        return super(DecimalEncoder, self).default(obj)


def fetch_dynamodb_items():
    """
    Fetch all items from the DynamoDB table.
    """
    table = dynamodb.Table(TABLE_NAME)
    response = table.scan()
    return response.get("Items", [])


def generate_presigned_url(s3_key):
    """
    Generate a presigned URL for a given S3 key.
    """
    try:
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600  # URL valid for 1 hour
        )
    except ClientError as e:
        print(f"Error generating presigned URL for {s3_key}: {str(e)}")
        return None


def enhance_item_with_presigned_urls(item):
    """
    Enhance a DynamoDB item with presigned URLs.
    """
    s3_key = item.get('audioS3Key')
    if not s3_key:
        print(f"Skipping item with missing 'audioS3Key': {item}")
        return None

    # Add presigned URL for audio
    item['presignedUrl'] = generate_presigned_url(s3_key)

    # Add presigned URL for album art if available
    album_art_key = item.get('albumArtS3Key')
    if album_art_key:
        item['albumArtUrl'] = generate_presigned_url(album_art_key)

    return item


def lambda_handler(event, context):
    try:
        # Step 1: Fetch items from DynamoDB
        items = fetch_dynamodb_items()

        # Step 2: Enhance each item with presigned URLs
        enhanced_tracks = [
            enhance_item_with_presigned_urls(item)
            for item in items if enhance_item_with_presigned_urls(item)
        ]

        # Step 3: Return the enhanced track list
        return build_response(200, json.dumps({"tracks": enhanced_tracks}, cls=DecimalEncoder))

    except ClientError as e:
        return build_response(500, json.dumps({"error": e.response['Error']['Message']}))
    except Exception as e:
        return build_response(500, json.dumps({"error": str(e)}))