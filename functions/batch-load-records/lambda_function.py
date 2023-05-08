import json
import boto3
import os

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # Get the S3 bucket and object key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Download the JSON file from the S3 bucket
    s3_object = s3.get_object(Bucket=bucket, Key=key)
    file_content = s3_object['Body'].read().decode('utf-8')
    data = json.loads(file_content)

    # Define the DynamoDB table
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    # Iterate over the JSON rows and batch write them to DynamoDB
    with table.batch_writer() as batch:
        for row in data:
            row['keywords'] = set(row['keywords'])  # Convert keywords to a string set
            batch.put_item(Item=row)

    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully processed {len(data)} records from {key}')
    }
