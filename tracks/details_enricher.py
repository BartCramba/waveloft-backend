import boto3, json, os, urllib.parse
dynamo  = boto3.resource("dynamodb")
tracks  = dynamo.Table(os.environ["TRACKS_TABLE"])
details = dynamo.Table(os.environ["DETAILS_TABLE"])
s3      = boto3.client("s3")

PROMOTE = {                       # fields you ALSO copy into Tracks
    "artist":   ("meta.artist",  "S"),
    "title":    ("track_fileName", "S"),  # fallback; will strip artist later
    "bpm":      ("features.bpm", "N"),
    "style":    ("meta.style",  "SS"),    # list → string-set
    "year":     ("meta.year",   "N"),
}

def _get(d, dotted):
    for k in dotted.split("."):
        if not isinstance(d, dict): return None
        d = d.get(k)
    return d

def lambda_handler(event, _context):
    for rec in event["Records"]:
        key   = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
        tid   = key.rsplit("/",1)[1].split(".",1)[0]
        body  = s3.get_object(Bucket=rec["s3"]["bucket"]["name"], Key=key)["Body"].read()
        data  = json.loads(body)

        # 1)  Put full JSON into TrackDetails (overwrites if you upload a new file)
        details.put_item(Item={
            "trackId": tid,
            "details": data,
            "metaS3Key": key,
        })

        # 2)  Promote chosen fields into Tracks *only if not already set*
        expr, vals, names = [], {}, {}
        for dest, (src, dtype) in PROMOTE.items():
            v = _get(data, src)
            if v is None: continue
            ph = f":{dest}"
            expr.append(f"{dest} = if_not_exists({dest}, {ph})")
            vals[ph] = {dtype: str(v) if dtype != "SS" else list(v)}
            if dest == "year": names["#year"] = "year"   # reserved word

        if expr:
            tracks.update_item(
                Key={"id": tid},
                UpdateExpression="SET " + ", ".join(expr),
                ExpressionAttributeNames=names or None,
                ExpressionAttributeValues=vals,
            )
