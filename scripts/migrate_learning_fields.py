import boto3, os, uuid
from utils.sm2 import MIN_EF      # reuse constant

TABLE = "Tracks"
PK_LEARNING = "DJ"

defaults = {
    "ease"        : 2.5,
    "reps"        : 0,
    "interval"    : 0,
    "nextReviewAt": "1970-01-01T00:00:00Z",
    "lastGuessAt" : None,
    "pkLearning"  : PK_LEARNING
}

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE)

scan_kwargs = {}
while True:
    batch = table.scan(**scan_kwargs)
    with table.batch_writer() as bw:
        for item in batch["Items"]:
            update = {k: v for k, v in defaults.items() if k not in item}
            if update:
                item.update(update)
                bw.put_item(Item=item)
    if "LastEvaluatedKey" not in batch:
        break
    scan_kwargs["ExclusiveStartKey"] = batch["LastEvaluatedKey"]

print("Migration done 🎉")
