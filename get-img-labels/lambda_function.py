import json
import boto3
import urllib.parse
import datetime
# based on HW2 index-photo
REGION = 'us-east-1'
TABLE = 'MaintenanceReports'

session = boto3.Session()

def update_report(reportID, new_labels):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE)
    
    # Retrieve the existing record from DynamoDB using the report ID
    response = table.get_item(Key={'reportID': reportID})
    item = response['Item']
    
    # Extract the existing set of labels from the record
    # Right now this will be an empty set, possible it will be pre-populated later
    if item.get('photo_labels'):
        existing_labels = item.get('photo_labels')
    
    # Add the new labels to the existing set
        updated_labels = existing_labels.append(new_labels)
    else:
        updated_labels = new_labels
    
    # Update the record in DynamoDB with the new labels
    table.update_item(
        Key={'reportID': reportID},
        UpdateExpression='SET photo_labels = :labels',
        ExpressionAttributeValues={':labels': updated_labels}
    )

def lambda_handler(event, context):
    print("event")
    s3_client = boto3.client('s3')
    rek_client = boto3.client('rekognition')
    bucket = event['Records'][0]['s3']['bucket']['name']
    # key_name should be the name of the photo
    key_name = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    # key_name should be in form {reportID}/{image_name} so split on '/' to get reportID
    reportID = key_name.split('/')[0]
    print(f'reportID is: {reportID}')
    
    
    # code adapted from https://serverlessland.com/snippets/integration-s3-to-lambda?utm_source=aws&utm_medium=link&utm_campaign=python&utm_id=docsamples
    try:
        response = s3_client.head_object(Bucket = bucket, Key = key_name)
        '''
        custom_labels = []
        if response["Metadata"]:
            print("METADATA IS:", response["Metadata"])
            
            if response["Metadata"]['customlabels']:
                json_labels = json.loads(response["Metadata"]['customlabels'])
                to_append = json_labels['labels']
                print("the custom labels are:", to_append)
                custom_labels = to_append
                
        
        print("The custom labels are", custom_labels)
        '''
        img_object = {'S3Object': {'Bucket': bucket, 'Name': key_name}}
    
        label_response = rek_client.detect_labels(
            Image=img_object)
        
        # build list of only the labels from the response
        labels = []
        for l in label_response["Labels"]:
            labels.add(l['Name'])

        print("Full set of labels are", labels)
        
        try:
            update_report(reportID, uni, labels)
        except Exception as UpdateProblem:
            print(UpdateProblem)
            print("Error updating report, probably the record doesn't exist")
            raise UpdateProblem
        
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key_name, bucket))
        raise e
    
    return {
        'statusCode': 200,
        'body': json.dumps('Successfully indexed photo')
    }


