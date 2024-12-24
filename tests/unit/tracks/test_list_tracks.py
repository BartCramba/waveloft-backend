import json

from tracks.list_tracks import lambda_handler

def test_list_tracks(setup_dynamodb):
    table = setup_dynamodb

    # Add some tracks to the DynamoDB table
    table.put_item(Item={"id": "1", "name": "Track 1", "artist": "Artist 1"})
    table.put_item(Item={"id": "2", "name": "Track 2", "artist": "Artist 2"})

    # Simulated API Gateway event
    event = {}
    context = {}

    # Run the Lambda function
    response = lambda_handler(event, context)
    response_body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "tracks" in response_body
    assert len(response_body["tracks"]) == 2
    assert {"id": "1", "name": "Track 1", "artist": "Artist 1"} in response_body["tracks"]
    assert {"id": "2", "name": "Track 2", "artist": "Artist 2"} in response_body["tracks"]