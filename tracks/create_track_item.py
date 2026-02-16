# tracks/create_track_item.py

import json
import os
import uuid
import boto3
from datetime import datetime, timezone

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]  # e.g. Tracks
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
}

def _resp(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }

def lambda_handler(event, context):
    try:
        method = (event.get("httpMethod") or "").upper()
        if method == "OPTIONS":
            return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

        raw = event.get("body") or "{}"
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})

        track_id = body.get("trackId") or str(uuid.uuid4())
        title = body.get("title", "Untitled Track")

        # Accept an explicit audioS3Key from the client (best for immediate playability)
        audio_key = body.get("audioS3Key") or "flac/pending"

        now_utc = datetime.now(timezone.utc).isoformat()
        item = {
            "id": track_id,
            "title": title,
            "audioS3Key": audio_key,
            "createdAt": now_utc,
        }

        table.put_item(Item=item)

        return _resp(
            200,
            {
                "success": True,
                "message": f"Track item created with id={track_id}",
                "item": item,
            },
        )

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return _resp(500, {"success": False, "message": str(e)})
