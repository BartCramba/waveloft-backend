import json
from decimal import Decimal

class _DecimalEncoder(json.JSONEncoder):
    """Turn decimal.Decimal → float so every response is valid JSON."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)         # or str(obj) if you prefer
        return super().default(obj)


def build_response(status_code, body, cors=True):
    headers = {
        "Content-Type": "application/json",
    }
    if cors:
        headers.update({
            "Access-Control-Allow-Origin": "*",  # Or specific origin
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS, PUT, DELETE",
            "Access-Control-Allow-Headers": "Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token"
        })

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, cls=_DecimalEncoder),
    }