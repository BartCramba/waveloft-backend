import boto3
from moto import mock_aws

@mock_aws
def test_create_table():
    # Set up the DynamoDB client
    conn = boto3.client("dynamodb", region_name="us-west-2")

    # Create a DynamoDB table
    conn.create_table(
        TableName="TestTable",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    # List tables and verify the table was created
    response = conn.list_tables()
    assert "TestTable" in response["TableNames"]

@mock_aws
def test_put_and_get_item():
    # Set up the DynamoDB client
    dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

    # Create a DynamoDB table
    table = dynamodb.create_table(
        TableName="TestTable",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Add an item
    table.put_item(Item={"id": "123", "name": "Test Item"})

    # Retrieve the item
    response = table.get_item(Key={"id": "123"})
    assert "Item" in response
    assert response["Item"]["name"] == "Test Item"

@mock_aws
def test_update_item():
    # Set up the DynamoDB client
    dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

    # Create a DynamoDB table
    table = dynamodb.create_table(
        TableName="TestTable",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Add an item
    table.put_item(Item={"id": "123", "name": "Old Name"})

    # Update the item
    table.update_item(
        Key={"id": "123"},
        UpdateExpression="SET #name = :value",
        ExpressionAttributeNames={"#name": "name"},
        ExpressionAttributeValues={":value": "New Name"},
    )

    # Retrieve the updated item
    response = table.get_item(Key={"id": "123"})
    assert response["Item"]["name"] == "New Name"

@mock_aws
def test_delete_item():
    # Set up the DynamoDB client
    dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

    # Create a DynamoDB table
    table = dynamodb.create_table(
        TableName="TestTable",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Add an item
    table.put_item(Item={"id": "123", "name": "Test Item"})

    # Delete the item
    table.delete_item(Key={"id": "123"})

    # Verify the item was deleted
    response = table.get_item(Key={"id": "123"})
    assert "Item" not in response