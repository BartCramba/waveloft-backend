import base64

import boto3
import pytest
from audio.upload_audio import lambda_handler

session = boto3.Session(profile_name="pablito")

def test_valid_input():
    event = {
        "queryStringParameters": {"filename": "test_audio.mp3"},
        "body": base64.b64encode(b"dummy content").decode("utf-8"),
    }
    context = {}
    response = lambda_handler(event, context)
    assert response["statusCode"] == 200
    assert "uploaded successfully" in response["body"]

def test_missing_filename():
    event = {
        "queryStringParameters": {},
        "body": base64.b64encode(b"dummy content").decode("utf-8"),
    }
    context = {}
    response = lambda_handler(event, context)
    assert response["statusCode"] == 400
    assert "Missing 'filename' in " in response["body"]

def test_invalid_base64_body():
    event = {
        "queryStringParameters": {"filename": "test_audio.mp3"},
        "body": "invalid_base64",
    }
    context = {}
    response = lambda_handler(event, context)
    assert response["statusCode"] == 400
    assert "Invalid base64" in response["body"]