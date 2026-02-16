import os
import json
import boto3
import logging
from boto3.dynamodb.conditions import Attr

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE"])

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token",
}

def _resp(status_code: int, body):
    if isinstance(body, str):
        # allow plain strings if you really want
        out = body
    else:
        out = json.dumps(body)
    return {"statusCode": status_code, "headers": CORS_HEADERS, "body": out}

def lambda_handler(event, _ctx):
    # OPTIONS preflight (in case API Gateway forwards it)
    if event.get("httpMethod") == "OPTIONS":
        return _resp(200, {"ok": True})

    qs = event.get("queryStringParameters") or {}
    fname = (qs.get("fileName") or "").strip()

    if not fname:
        return _resp(400, {"error": "fileName required"})

    # IMPORTANT:
    # DynamoDB Scan + FilterExpression + Limit=1 is incorrect (it only evaluates 1 item).
    # We must paginate scan until we find a match or we reach the end.
    start_key = None

    try:
        while True:
            scan_kwargs = {
                "ProjectionExpression": "id, fileName",
                "FilterExpression": Attr("fileName").eq(fname),
            }
            if start_key:
                scan_kwargs["ExclusiveStartKey"] = start_key

            resp = table.scan(**scan_kwargs)
            items = resp.get("Items") or []

            if items:
                # if multiple match (shouldn't), return first
                return _resp(200, items[0])

            start_key = resp.get("LastEvaluatedKey")
            if not start_key:
                break

        return _resp(404, {"error": "not found", "fileName": fname})

    except Exception as e:
        log.exception("lookup_by_filename failed")
        return _resp(500, {"error": str(e)})
