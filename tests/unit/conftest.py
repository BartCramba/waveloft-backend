import pytest
from moto import mock_aws
import boto3

@pytest.fixture
def setup_dynamodb():
    # Mock AWS environment
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource("dynamodb", region_name="eu-north-1")

        # Delete any existing table (if it exists in the mock environment)
        try:
            table = dynamodb.Table("Tracks")
            table.delete()
            table.wait_until_not_exists()
        except Exception:
            pass  # Ignore if the table doesn't exist

        # Create the table
        table = dynamodb.create_table(
            TableName="Tracks",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield table

        # Cleanup after test (not strictly necessary for mock_aws)
        table.delete()
        table.wait_until_not_exists()