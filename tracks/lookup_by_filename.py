# tracks/lookup_by_filename.py  (new)
import os, json, boto3
table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE"])

def lambda_handler(event, _):
    q = event["queryStringParameters"] or {}
    fname = q.get("fileName")
    if not fname:
        return {"statusCode": 400, "body": "fileName required"}

    resp = table.scan(
        ProjectionExpression="id, fileName",
        FilterExpression="fileName = :f",
        ExpressionAttributeValues={":f": fname},
        Limit=1,
    )
    if resp["Items"]:
        return {"statusCode": 200, "body": json.dumps(resp["Items"][0])}
    return {"statusCode": 404, "body": "not found"}
