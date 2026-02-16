import boto3
import json
import os
import urllib.parse
import logging
from decimal import Decimal
from datetime import datetime, timezone

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

dynamo  = boto3.resource("dynamodb")
tracks  = dynamo.Table(os.environ["TRACKS_TABLE"])
details = dynamo.Table(os.environ["DETAILS_TABLE"])
s3      = boto3.client("s3")

# Promote these fields into the hot Tracks table for fast filtering + GuessTheTrack display.
# Each dest has candidate dotted paths (first match wins) and a target type.
PROMOTE = {
    "artist":       {"paths": ["meta.artist", "artist"], "type": "S"},
    "title":        {"paths": ["meta.title", "title"], "type": "S"},
    "moods":        {"paths": ["meta.moods", "moods"], "type": "SS"},
    "danceability": {"paths": ["features.danceability", "danceability"], "type": "N"},

    # Optional (keep if you already have them / want filters later)
    "bpm":          {"paths": ["features.bpm", "bpm"], "type": "N"},
    "year":         {"paths": ["meta.year", "year"], "type": "N"},
    "style":        {"paths": ["meta.style", "style"], "type": "SS"},
}

def _get(d, dotted):
    cur = d
    for k in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur

def _first_value(d, paths):
    for p in paths:
        v = _get(d, p)
        if v is not None:
            return v
    return None

def _to_decimal(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        # Dynamo treats bool separately; do not coerce
        return None
    if isinstance(v, int):
        return Decimal(str(v))
    if isinstance(v, float):
        # should not happen because we parse_float=Decimal, but keep safe
        return Decimal(str(v))
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return Decimal(s)
        except Exception:
            return None
    return None

def _to_string(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

def _to_string_set(v):
    if v is None:
        return None

    items = []
    if isinstance(v, (list, tuple, set)):
        items = list(v)
    elif isinstance(v, str):
        # allow "day, night; open-air"
        raw = v.replace(";", ",").replace("\n", ",")
        items = [x.strip() for x in raw.split(",")]
    else:
        items = [str(v)]

    out = {str(x).strip() for x in items if str(x).strip()}
    return out if out else None

def _coerce_value(v, dtype):
    if dtype == "S":
        return _to_string(v)
    if dtype == "N":
        return _to_decimal(v)
    if dtype == "SS":
        return _to_string_set(v)
    return None

def lambda_handler(event, _context):
    for rec in event.get("Records", []):
        try:
            key = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
            bucket = rec["s3"]["bucket"]["name"]

            # Expect meta/<trackId>.json
            tid = key.rsplit("/", 1)[1].split(".", 1)[0]

            obj = s3.get_object(Bucket=bucket, Key=key)
            raw = obj["Body"].read()

            # Parse floats as Decimal (prevents DynamoDB float error)
            data = json.loads(raw.decode("utf-8"), parse_float=Decimal)

            now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

            # 1) Store full JSON in TrackDetails
            details.put_item(Item={
                "trackId": tid,
                "details": data,
                "metaS3Key": key,
                "updatedAt": now_iso,
            })

            # 2) Promote selected fields into Tracks (overwrite to allow manual corrections)
            set_parts = []
            names = {}
            values = {}
            i = 0

            for dest, rule in PROMOTE.items():
                v_raw = _first_value(data, rule["paths"])
                v = _coerce_value(v_raw, rule["type"])
                if v is None:
                    continue

                nk = f"#f{i}"
                vk = f":v{i}"
                names[nk] = dest
                values[vk] = v
                set_parts.append(f"{nk} = {vk}")
                i += 1

            # Always update these debug fields so you can see ingestion state in Tracks
            nk = f"#f{i}"; vk = f":v{i}"
            names[nk] = "metaS3Key"
            values[vk] = key
            set_parts.append(f"{nk} = {vk}")
            i += 1

            nk = f"#f{i}"; vk = f":v{i}"
            names[nk] = "metaUpdatedAt"
            values[vk] = now_iso
            set_parts.append(f"{nk} = {vk}")
            i += 1

            if set_parts:
                tracks.update_item(
                    Key={"id": tid},
                    UpdateExpression="SET " + ", ".join(set_parts),
                    ExpressionAttributeNames=names,
                    ExpressionAttributeValues=values,
                )

            log.info("details_enricher OK trackId=%s key=%s promoted=%d", tid, key, len(set_parts))

        except Exception as e:
            log.exception("details_enricher FAILED record=%s err=%s", json.dumps(rec)[:5000], str(e))

    return {"statusCode": 200, "body": "ok"}
