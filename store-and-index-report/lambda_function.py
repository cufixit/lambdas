import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
import urllib.parse
import datetime
from requests_aws4auth import AWS4Auth

# imported from my index-photos lambda HW2 - Jesse
REGION = 'us-east-1'
HOST = "search-fixit-report-index-eetuasoopiwimto5tsjpg2maju.us-east-1.es.amazonaws.com"
INDEX = 'reports'
TABLE = 'MaintenanceReports'
BUCKET = 'cu-fixit-photos'
KEYWORD_Q = "https://sqs.us-east-1.amazonaws.com/662545362847/KeywordQueue"

session = boto3.Session()

def get_awsauth(region, service):
    cred = session.get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)

def index_report(b, name):
    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)
    # use client.index() to update/overwrite an existing index
    # however because I'm using a timestamp as index id, every time I run a test
    # it creates a new index. 
    #res = client.create(index=INDEX, body=b, id=name)
    # because I'm now using reportID for id, it's possible that the same record can be indexed twice
    # which is what I want, but need to use client.index instead of client.
    res = client.index(index=INDEX, body=b, id=name)

def send_queue(txt):
    sqs = boto3.client("sqs")
    sqs_response = sqs.send_message(
            QueueUrl=KEYWORD_Q, MessageBody=json.dumps(txt)
        )
    return sqs_response

def lambda_handler(event, context):
    ''' 
    # pull one item from queue to test
    sqs_client = boto3.client('sqs', region_name=REGION)
    
    q_rsp = sqs_client.receive_message(
        QueueUrl=Q_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
    )
    print(f"New event from queue: {q_rsp}")
    sqs_client.delete_message(QueueUrl = Q_URL, ReceiptHandle=msg_receipt_handle)
    '''
    print(f"New event from queue: {event}")
    message = event['Records'][0]['body']
    report_info = json.loads(message)
    # print(f"the message is: {message}")
    reportID = report_info['reportId']
    userID = report_info['userId']
    location = report_info["location"]
    description = report_info["description"]
    # print(f"the reportID is {reportID} and userID is {userID}")
    
    try:
        
        timestamp = datetime.datetime.now()
        date = timestamp.strftime("%m/%d/%Y")
        print(f'the date is {date}')
        # response = put_report(report, reportID, timestamp)
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE)
        # don't store photo urls. Get requests will need to generate presigned urls based on bucket name and object key
        response = table.put_item(
            Item={
                'reportID': reportID,
                'userID': userID,
                'title': report_info["title"],
                'location': location,
                'description': report_info["description"],
                'date': date,
                'bucket': BUCKET,
                'imageKeys': report_info["imageKeys"],
                'status': 'CREATED', # hardcode CREATED status for all new reports
                'photo_labels': None,
                'keywords': None
            }
        )
        
        print(f"Successfully put report in dynamo. This is the response: {response}")
        
        # should I also index photo labels and keywords?
        to_idx = {
            "reportID": reportID, 
            "date": date, 
            'userID': userID,
            'location': location,
            'status': 'CREATED'
        }
        
        index = json.dumps(to_idx, default=str)
        index_report(index, reportID)
        print("this is what you indexed", index)
        
        
    except Exception as e:
        print(e)
        print('Error getting object {} from queue. Make sure they exist and your bucket is in the same region as this function.'.format(reportID))
        raise e
    
    txt = {
        "reportID": reportID,
        "description": description
        
    }
    sqs_response = send_queue(txt)
    print(sqs_response)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Successfully indexed report')
    }
