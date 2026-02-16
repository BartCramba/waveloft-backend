from decimal import Decimal
import logging
import json
import os
from datetime import datetime, timezone

import boto3

from sm2 import apply_sm2, next_review_at
from cors_utils import build_response

TABLE_NAME = os.environ["DYNAMODB_TABLE"]
LEARNING_PK = os.environ.get("LEARNING_PK", "DJ")

table = boto3.resource("dynamodb").Table(TABLE_NAME)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def lambda_handler(event, _ctx):
    try:
        # CORS preflight
        if event.get("httpMethod") == "OPTIONS":
            return build_response(200, {"ok": True})

        body_raw = event.get("body") or "{}"
        body = json.loads(body_raw)

        track_id = body.get("trackId")
        grade = body.get("grade")

        if not track_id:
            return build_response(400, {"error": "Missing trackId"})
        if grade is None:
            return build_response(400, {"error": "Missing grade"})

        grade = int(grade)
        if grade < 0 or grade > 5:
            return build_response(400, {"error": "grade must be 0..5"})

        item = table.get_item(Key={"id": track_id}).get("Item")
        if not item:
            return build_response(404, {"error": "Track not found"})

        ease = float(item.get("ease", 2.5))
        reps = int(item.get("reps", 0))
        inter = int(item.get("interval", 0))

        new_ease, new_reps, new_int = apply_sm2(ease, reps, inter, grade)
        next_at = next_review_at(new_int)
        now_iso = datetime.now(timezone.utc).isoformat()

        table.update_item(
            Key={"id": track_id},
            UpdateExpression="""
                SET ease=:e, reps=:r, #int=:i,
                    nextReviewAt=:n, lastGuessAt=:l, pkLearning=:pk
            """,
            ExpressionAttributeNames={"#int": "interval"},
            ExpressionAttributeValues={
                ":e": Decimal(str(round(new_ease, 4))),
                ":r": Decimal(str(new_reps)),
                ":i": Decimal(str(new_int)),
                ":n": next_at,
                ":l": now_iso,
                ":pk": LEARNING_PK,
            },
        )

        return build_response(200, {"ok": True, "trackId": track_id, "nextReviewAt": next_at})

    except Exception as e:
        log.exception("grade failed")
        return build_response(500, {"error": str(e)})
