import json
from tracks.create_track import lambda_handler

def test_create_track_valid(setup_dynamodb):
    # Simulated API Gateway event
    event = {
        "body": json.dumps({"name": "Test Track", "artist": "Test Artist"})
    }
    context = {}

    # Run the Lambda function
    response = lambda_handler(event, context)
    response_body = json.loads(response["body"])

    assert response["statusCode"] == 201
    assert response_body["message"] == "Track created"
    assert "id" in response_body

    # Verify the track was added to DynamoDB
    table = setup_dynamodb
    result = table.get_item(Key={"id": response_body["id"]})
    assert "Item" in result
    assert result["Item"]["name"] == "Test Track"
    assert result["Item"]["artist"] == "Test Artist"

def test_create_track_missing_fields(setup_dynamodb):
    # Simulated API Gateway event with missing fields
    event = {"body": json.dumps({"name": "Incomplete Track"})}
    context = {}

    # Run the Lambda function
    response = lambda_handler(event, context)

    # Check for error response (you may need to add error handling in your function)
    assert response["statusCode"] == 400