import boto3
import base64
import json

def test_integration_lambda_handler():
    # AWS clients
    lambda_client = boto3.client("lambda")
    s3_client = boto3.client("s3")
    bucket_name = "wave-loft-audio-bucket"

    # Create event
    event = {
        "queryStringParameters": {"filename": "test_audio.mp3"},
        "body": base64.b64encode(b"dummy content").decode("utf-8"),
    }

    # Invoke the Lambda function
    response = lambda_client.invoke(
        FunctionName="UploadAudioFunction",
        Payload=json.dumps(event),
    )
    payload = json.loads(response["Payload"].read())

    # Assertions
    assert payload["statusCode"] == 200
    assert "uploaded successfully" in payload["body"]

    # Verify file in S3
    obj = s3_client.get_object(Bucket=bucket_name, Key="test_audio.mp3")
    assert obj["Body"].read() == b"dummy content"