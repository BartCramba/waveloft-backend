from tracks.delete_track import lambda_handler
import json

def test_delete_track_valid(setup_dynamodb):
    table = setup_dynamodb

    # Add a track to DynamoDB
    table.put_item(Item={"id": "123", "name": "Test Track", "artist": "Test Artist"})

    # Simulated API Gateway event
    event = {"pathParameters": {"id": "123"}}
    context = {}

    # Run the Lambda function
    response = lambda_handler(event, context)
    response_body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert response_body["message"] == "Track deleted"

    # Verify the track was deleted from DynamoDB
    result = table.get_item(Key={"id": "123"})
    assert "Item" not in result

def test_delete_track_non_existent(setup_dynamodb):
    # Simulated API Gateway event
    event = {"pathParameters": {"id": "999"}}
    context = {}

    # Run the Lambda function
    response = lambda_handler(event, context)
    response_body = json.loads(response["body"])

    # DynamoDB delete_item is idempotent; no error for non-existent items
    assert response["statusCode"] == 200
    assert response_body["message"] == "Track deleted"