# create_track_item.py

import json
import os
import uuid
import boto3
from datetime import datetime, timezone

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]  # e.g. Tracks
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event, context):
    """
    Minimal endpoint that creates a 'Track' item in DynamoDB with:
      - id = the trackId we either generate or read from client
      - optional title, or placeholders
      - audioS3Key = "pending" or "none"
      - createdAt timestamp

    Expects JSON body like:
    {
      "trackId": "...",  # optional if you want the client to supply
      "title": "..."     # optional
    }

    Returns JSON:
    {
      "message": "Track item created with id=xxx",
      "item": { ... the full item you wrote to DB ... }
    }
    """
    try:
        body = json.loads(event["body"]) if event.get("body") else {}
        track_id = body.get("trackId")
        if not track_id:
            # If the client didn't pass one, we generate
            track_id = str(uuid.uuid4())

        title = body.get("title", "Untitled Track")

        # Build the minimal item
        now_utc = datetime.now(timezone.utc).isoformat()
        item = {
            "id": track_id,
            "title": title,
            "audioS3Key": "flac/pending",  # or just "none"
            "createdAt": now_utc
        }

        # Put to Dynamo
        table.put_item(Item=item)

        response_body = {
            "message": f"Track item created with id={track_id}",
            "item": item
        }
        return {
            "statusCode": 200,
            "body": json.dumps(response_body)
        }

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
