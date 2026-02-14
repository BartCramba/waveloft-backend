import os, json
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

from cors_utils import build_response

TABLE_NAME   = os.environ["DYNAMODB_TABLE"]
BUCKET_NAME  = os.environ["BUCKET_NAME"]
LEARNING_PK  = os.environ.get("LEARNING_PK", "DJ")
DEFAULT_LIMIT = 30

ddb  = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)
s3   = boto3.client("s3")

def lambda_handler(event, _ctx):
    try:
        qs = event.get("queryStringParameters") or {}  # << fix
        limit = int(qs.get("limit", DEFAULT_LIMIT))

        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        resp = table.query(
            IndexName="LearningIndex",
            KeyConditionExpression=Key("pkLearning").eq(LEARNING_PK) &
                                    Key("nextReviewAt").lte(now_iso),
            Limit=limit,
            ScanIndexForward=True
        )
        items = resp.get("Items", [])

        # -------- attach presigned URLs & filter pending rows --------------------
        playable = []
        for it in items:
            key = it.get("audioS3Key")
            if not key or key.endswith("/pending"):
                # skip items that haven’t been transcoded yet
                continue

            it["presignedUrl"] = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET_NAME, "Key": key},
                ExpiresIn=86_400           # 24 h
            )
            playable.append(it)

        return build_response(200, {"tracks": items})

    except Exception as e:
        return build_response(500, {"error": str(e)})
