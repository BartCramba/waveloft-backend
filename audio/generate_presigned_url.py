import boto3
import os
import json
from botocore.exceptions import ClientError
from cors_utils import build_response

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

TABLE_NAME = os.environ['DYNAMODB_TABLE']
BUCKET_NAME = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    try:
        # Fetch all items from DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        response = table.scan()
        items = response.get("Items", [])

        # Enhance metadata with presigned URLs
        enhanced_tracks = []
        for item in items:
            s3_key = item['s3Key']
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=3600  # URL valid for 1 hour
            )
            item['presignedUrl'] = presigned_url
            enhanced_tracks.append(item)

        # Return enhanced track list
        return build_response(200, json.dumps({"tracks": enhanced_tracks}))
    except ClientError as e:
        return build_response(500, json.dumps({"error": e.response['Error']['Message']}))
    except Exception as e:
        return build_response(500, json.dumps({"error": str(e)}))