import json
from tracks.update_track import lambda_handler  # Replace `your_module` with the actual file path

def test_update_track_valid(setup_dynamodb):
    table = setup_dynamodb

    # Add a track to DynamoDB
    table.put_item(Item={"id": "123", "name": "Old Track", "artist": "Old Artist"})

    # Simulated API Gateway event
    event = {
        "pathParameters": {"id": "123"},
        "body": json.dumps({"name": "Updated Track", "artist": "Updated Artist"})
    }
    context = {}

    # Run the Lambda function
    response = lambda_handler(event, context)
    response_body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert response_body["message"] == "Track updated"
    assert response_body["updatedAttributes"] == {"name": "Updated Track", "artist": "Updated Artist"}

    # Verify the updated values in DynamoDB
    result = table.get_item(Key={"id": "123"})
    assert "Item" in result
    assert result["Item"]["name"] == "Updated Track"
    assert result["Item"]["artist"] == "Updated Artist"


def test_update_track_non_existent(setup_dynamodb):
    # Simulated API Gateway event for a non-existent track
    event = {
        "pathParameters": {"id": "999"},
        "body": json.dumps({"name": "New Track", "artist": "New Artist"})
    }
    context = {}

    # Run the Lambda function
    response = lambda_handler(event, context)
    response_body = json.loads(response["body"])

    # Check for successful update of a non-existent item
    assert response["statusCode"] == 200
    assert response_body["message"] == "Track updated"
    assert response_body["updatedAttributes"] == {"id": "999", "name": "New Track", "artist": "New Artist"}
