from decimal import Decimal
import logging, json, os
from datetime import datetime, timezone
import boto3
from sm2 import apply_sm2, next_review_at

TABLE_NAME  = os.environ["DYNAMODB_TABLE"]
LEARNING_PK = os.environ.get("LEARNING_PK", "DJ")

table = boto3.resource("dynamodb").Table(TABLE_NAME)
log   = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def lambda_handler(event, _ctx):
    try:
        body = json.loads(event["body"])
        track_id, grade = body["trackId"], int(body["grade"])

        item = table.get_item(Key={"id": track_id}).get("Item")
        if not item:
            return {"statusCode": 404,
                    "body": json.dumps({"error": "Track not found"})}

        ease  = float(item.get("ease", 2.5))
        reps  = int(item.get("reps", 0))
        inter = int(item.get("interval", 0))

        new_ease, new_reps, new_int = apply_sm2(ease, reps, inter, grade)

        table.update_item(
            Key={"id": track_id},
            UpdateExpression="""
                SET ease=:e, reps=:r, #int=:i,
                    nextReviewAt=:n, lastGuessAt=:l, pkLearning=:pk
            """,
            ExpressionAttributeNames={ "#int": "interval" },   # ← here
            ExpressionAttributeValues={
                ":e": Decimal(str(round(new_ease, 4))),  # already good
                ":r": Decimal(str(new_reps)),  # ← was int
                ":i": Decimal(str(new_int)),  # ← was int/float
                ":n": next_review_at(new_int),
                ":l": datetime.now(timezone.utc).isoformat(),
                ":pk": LEARNING_PK
            }
        )

        return {"statusCode": 200, "body": json.dumps({"ok": True})}

    except Exception as e:
        log.exception("grade failed")               # prints stack-trace
        return {"statusCode": 500,
                "body": json.dumps({"error": str(e)})}
