# WaveLoft Backend

Serverless REST API powering the WaveLoft Electron DJ app. Manages a track library stored in S3 with metadata in DynamoDB and implements a **spaced-repetition "Guess The Track"** learning system (SM-2 algorithm).

## How It Connects to the Electron App

```
Electron App                        AWS Cloud
+--------------+    HTTPS     +------------------+     +-----------+
| WaveLoft UI  | ----------> | API Gateway      | --> | Lambda    |
| (local cache)|             | (REST, /Prod)    |     | functions |
+--------------+    S3       +------------------+     +-----------+
       |        presigned          |                        |
       +------------------------->| S3 Bucket              | DynamoDB
         upload / download        | (wave-loft-audio-bucket)|
                                  +------------------------+
```

1. The Electron app uploads audio (FLAC/MP3) to S3 via **presigned URLs** obtained from the API.
2. FLAC uploads trigger automatic **transcoding to 320 kbps MP3** via a Lambda + FFmpeg.
3. The app calls REST endpoints for CRUD, retrieves presigned download URLs, and plays cached MP3s.
4. The "Guess The Track" feature uses `GET /due` and `POST /grade` to drive spaced-repetition review scheduling.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| IaC | AWS SAM (CloudFormation) |
| Compute | AWS Lambda (13 functions) |
| API | Amazon API Gateway (REST) |
| Database | Amazon DynamoDB (2 tables, 1 GSI) |
| Storage | Amazon S3 |
| Auth | Amazon Cognito Identity Pool (unauthenticated uploads) |
| Audio processing | Mutagen (metadata), FFmpeg (transcoding) |
| Testing | pytest + moto (AWS mocking) |

---

## Local Setup

### Prerequisites

- **Python 3.12+**
- **AWS SAM CLI** ([install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html))
- **Docker** (for `sam build --use-container` and `sam local`)
- **AWS CLI** configured with a profile named `admin-user` (or edit `samconfig.toml:21`)

### Install Dependencies

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# SAM will install Lambda dependencies (mutagen) automatically during build
```

### Build

```bash
sam build --use-container
```

The build is cached and parallel by default (`samconfig.toml:9-10`).

### Run Locally

```bash
# Start the full API locally on port 3000
sam local start-api

# Invoke a single function with a test event
sam local invoke CreateTrackFunction --event events/event.json
```

Warm containers are enabled for local development (`samconfig.toml:34-37`).

### Run Tests

```bash
# Unit tests
python -m pytest tests/unit -v

# Integration tests (requires a deployed stack)
AWS_SAM_STACK_NAME="music-api-stack" python -m pytest tests/integration -v
```

---

## Configuration

### Environment Variables (set per-Lambda in `template.yaml`)

| Variable | Default | Used By | Description |
|----------|---------|---------|-------------|
| `DYNAMODB_TABLE` | `Tracks` | Most functions | Primary DynamoDB table name |
| `S3_BUCKET` / `BUCKET_NAME` | `wave-loft-audio-bucket` | Audio + track functions | S3 bucket for audio and art |
| `LEARNING_PK` | `DJ` | Due/grade functions | Constant partition key for the learning GSI |
| `TRACKS_TABLE` | `Tracks` | DetailsEnricher | Tracks table (ref) |
| `DETAILS_TABLE` | `TrackDetails` | DetailsEnricher | Rich metadata cold-store table |

### SAM Parameters (`template.yaml:4-11`)

| Parameter | Default |
|-----------|---------|
| `MyBucketName` | `wave-loft-audio-bucket` |
| `LearningPK` | `DJ` |

### Deployment Config (`samconfig.toml`)

| Key | Value |
|-----|-------|
| Stack name | `music-api-stack` |
| Region | `eu-north-1` |
| AWS profile | `admin-user` |
| IAM capability | `CAPABILITY_IAM` |

---

## API Quick Reference

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/tracks` | Create tracks from uploaded S3 audio files |
| `GET` | `/tracks` | List all tracks (no presigned URLs) |
| `PUT` | `/tracks/{id}` | Update track name/artist |
| `DELETE` | `/tracks/{id}` | Delete a track |
| `POST` | `/trackItems` | Create a placeholder track item |
| `GET` | `/due` | Get tracks due for spaced-repetition review |
| `POST` | `/grade` | Submit a grade (0-5) for a reviewed track |
| `GET` | `/lookup?fileName=...` | Find track ID by filename |
| `POST` | `/upload/presigned` | Get presigned S3 upload URLs |
| `GET` | `/download/presigned` | Get presigned S3 download URLs for all tracks |
| `POST` | `/upload` | Direct multipart audio upload |

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for full request/response schemas.

### Quick Examples

**Create tracks** (after uploading audio to S3):
```bash
curl -X POST https://<api-id>.execute-api.eu-north-1.amazonaws.com/Prod/tracks \
  -H "Content-Type: application/json" \
  -d '{
    "files": [{
      "trackId": "550e8400-e29b-41d4-a716-446655440000",
      "fileName": "DeepHouse_Mix.flac",
      "s3Key": "flac/DeepHouse_Mix.flac"
    }]
  }'
```

**Get presigned download URLs**:
```bash
curl https://<api-id>.execute-api.eu-north-1.amazonaws.com/Prod/download/presigned
```

**Submit a guess grade**:
```bash
curl -X POST https://<api-id>.execute-api.eu-north-1.amazonaws.com/Prod/grade \
  -H "Content-Type: application/json" \
  -d '{"trackId": "550e8400-e29b-41d4-a716-446655440000", "grade": 4}'
```

---

## Deployment

```bash
# First-time guided deploy
sam deploy --guided

# Subsequent deploys (uses samconfig.toml)
sam deploy

# Validate template
sam validate --lint
```

The API Gateway endpoint URL is printed in the CloudFormation Outputs as `WaveLoftApiUrl` (`template.yaml:1005-1007`).

### Teardown

```bash
sam delete --stack-name music-api-stack
```

**Note:** The S3 bucket must be emptied before stack deletion (CloudFormation cannot delete non-empty buckets).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `sam build` fails on mutagen | Ensure Docker is running; use `--use-container` |
| Presigned URLs return 403 | Check IAM permissions and S3 bucket policy; verify `eu-north-1` region in S3 client config (`audio/generate_presigned_url_download.py:11-21`) |
| FLAC transcode Lambda timeout | File is very large; current timeout is 300s / 2048 MB (`template.yaml:815-816`) |
| `module 'cors_utils' not found` | Ensure `UtilsLayer` is attached to the function in `template.yaml` |
| DynamoDB `Decimal` serialization error | All handlers should use `_DecimalEncoder` from `cors_utils` (`utils/python/cors_utils.py:4-9`) |
| Transcode doesn't update DB | The S3 upload must include `x-amz-meta-trackid` in object metadata (`transcode/transcode.py:46-48`) |
| `sam local start-api` is slow | Already using `warm_containers = "EAGER"` (`samconfig.toml:34`) |

---

## Further Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design, request lifecycle, Mermaid diagrams
- [API Reference](docs/API_REFERENCE.md) - Full endpoint documentation
- [Data Model](docs/DATA_MODEL.md) - DynamoDB schema, entities, indexes
- [LLM Handoff](docs/LLM_HANDOFF.md) - Quick-start brief for AI assistants or new developers
