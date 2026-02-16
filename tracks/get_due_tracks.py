# tracks/get_due_tracks.py
import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

from cors_utils import build_response

TABLE_NAME = os.environ["DYNAMODB_TABLE"]
BUCKET_NAME = os.environ["BUCKET_NAME"]
LEARNING_PK = os.environ.get("LEARNING_PK", "DJ")

DEFAULT_LIMIT = 40
# Keep this <= your Lambda role credential lifetime; 3600 is safe.
PRESIGN_EXPIRES_SEC = int(os.environ.get("PRESIGN_EXPIRES_SEC", "3600"))

ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)
s3 = boto3.client("s3")


def _is_pending_key(key: str) -> bool:
    k = (key or "").strip().lower()
    return k.endswith("/pending") or k == "flac/pending" or k.endswith("flac/pending")


def _looks_like_mp3(key: str) -> bool:
    k = (key or "").lower().strip()
    return k.endswith(".mp3") or k.startswith("mp3/")


def lambda_handler(event, _ctx):
    try:
        # Preflight safety (in case your API forwards OPTIONS)
        if (event.get("httpMethod") or "").upper() == "OPTIONS":
            return build_response(200, {"ok": True})

        qs = event.get("queryStringParameters") or {}
        try:
            limit = int(qs.get("limit", DEFAULT_LIMIT))
        except Exception:
            limit = DEFAULT_LIMIT

        # ISO string compare works because all are UTC ISO8601
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        playable = []
        skipped = {"pending": 0, "not_mp3": 0, "missing_key": 0}

        # We may need to fetch more than `limit` items to end up with `limit` playable
        # (because we filter pending / non-mp3).
        start_key = None
        page_limit = max(50, limit * 3)

        while len(playable) < limit:
            kwargs = {
                "IndexName": "LearningIndex",
                "KeyConditionExpression": Key("pkLearning").eq(LEARNING_PK)
                & Key("nextReviewAt").lte(now_iso),
                "Limit": page_limit,
                "ScanIndexForward": True,
            }
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key

            resp = table.query(**kwargs)
            items = resp.get("Items", [])

            for it in items:
                key = it.get("audioS3Key")
                if not key:
                    skipped["missing_key"] += 1
                    continue
                if _is_pending_key(key):
                    skipped["pending"] += 1
                    continue
                if not _looks_like_mp3(key):
                    skipped["not_mp3"] += 1
                    continue

                # Attach presigned URL
                it = dict(it)  # avoid mutating the DDB response object
                it["presignedUrl"] = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": BUCKET_NAME, "Key": key},
                    ExpiresIn=PRESIGN_EXPIRES_SEC,
                )
                playable.append(it)
                if len(playable) >= limit:
                    break

            start_key = resp.get("LastEvaluatedKey")
            if not start_key:
                break

        return build_response(
            200,
            {
                "tracks": playable,
                "count": len(playable),
                "now": now_iso,
                "skipped": skipped,
            },
        )

    except Exception as e:
        return build_response(500, {"error": str(e)})
