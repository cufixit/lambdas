import re
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from botocore.exceptions import ClientError
from inflection import singularize

# based on hw2 search-photos
REGION = "us-east-1"
HOST = "search-fixit-report-index-eetuasoopiwimto5tsjpg2maju.us-east-1.es.amazonaws.com"
INDEX = "reports"
TABLE = "MaintenanceReports"

session = boto3.Session()


def generate_presigned_url(bucket, object_key):
    s3_client = boto3.client("s3")
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=3600,
        )
    except ClientError as e:
        print(e)
        print("Couldn't generate presigned url")
        return None
    print("The pre-signed url is", url)
    return url


def query(keywords):
    # keywords = clean_keywords(keywords) Don't clean for now because you aren't storing as lowercase in dynamo
    print("Cleaned up keywords:", keywords)

    q = {"size": 100, "query": {"multi_match": {"query": keywords}}}

    client = OpenSearch(
        hosts=[{"host": HOST, "port": 443}],
        http_auth=get_awsauth(REGION, "es"),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

    res = client.search(index=INDEX, body=q)
    print(res)

    hits = res["hits"]["hits"]
    results = [hit["_source"]["reportID"] for hit in hits]
    """
    for hit in hits:
        results.append(hit['_source']['reportID'])
    """
    return results


def clean_keywords(keywords):
    keywords = [
        part.strip()
        for keyword in keywords
        for part in re.sub(r"(?: and | in | the | a )", ",", keyword).split(",")
    ]
    keywords = list(filter(bool, keywords))
    keywords = [re.sub(r"\s+", "", keyword) for keyword in keywords]
    keywords = [keyword.lower() for keyword in keywords]
    keywords = [singularize(keyword) for keyword in keywords]

    return keywords


def get_awsauth(region, service):
    cred = session.get_credentials()
    return AWS4Auth(
        cred.access_key, cred.secret_key, region, service, session_token=cred.token
    )


def parse_dynamo(rest):
    # json_result = {"restaurants": []}

    addr_line1 = str(rest["address"]["L"][0]["S"])
    addr_line2 = str(rest["address"]["L"][1]["S"])
    addr_full = addr_line1 + "\n" + addr_line2
    rest_name = str(rest["name"]["S"])
    rating = str(rest["rating"]["N"])
    rev_cnt = str(rest["review_count"]["N"])

    res = {
        "address": addr_full,
        "name": rest_name,
        "rating": rating,
        "review count": rev_cnt,
    }
    # json_result["restaurants"].append(res)
    # return res or json_result?
    return res


def dynamo_scan():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE)

    response = table.scan()

    items = response["Items"]

    print("first set of items are:", items)
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])
    for item in items:
        bucket = item["bucket"]
        img_keys = item["imageKeys"]
        url_list = [generate_presigned_url(bucket, img) for img in img_keys]
        item["urls"] = url_list

    print(f"The items are: {items}")

    return items


def dynamodb_lookup(id):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE)

    response = table.get_item(Key={"reportID": id})
    item = response.get("Item")
    if not item:
        return None

    bucket = item.get("bucket")
    img_keys = item.get("imageKeys", [])
    url_list = [generate_presigned_url(bucket, img) for img in img_keys]
    item["urls"] = url_list
    return item


# TODO modify update_report to update based on the given flag
# For now it only sets the status to "REVIEWED"
def update_report(reportID, to_update="REVIEWED", flag="status"):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE)

    # Retrieve the existing record from DynamoDB using the report ID
    response = table.get_item(Key={"reportID": reportID})
    item = response["Item"]
    # print(f"Successfully got item: {response}")
    # Extract the existing set of labels from the record
    # Right now this will be an empty set, possible it will be pre-populated later
    cur_status = item.get("status")

    # Update the record in DynamoDB with the new labels
    update = table.update_item(
        Key={"reportID": reportID},
        UpdateExpression="SET #status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": to_update},
    )

    # print(f"The table updated successfully: {update}")


def lambda_handler(event, context):
    print(f"the event is: {event}")
    # user_query = event.get("q")

    cors = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credientials": "true",
        "Access-Control-Allow-Methods": "GET, OPTIONS, POST",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    reportID = None

    if path_params := event["pathParameters"]:
        reportID = path_params.get(
            "reportId"
        )  # note that the "d" is not capalized in reportId

    try:
        if reportID:
            print(
                "You should not be making into this part if you are testing empty query"
            )
            user_query = reportID
            dynamoIDs = query(
                user_query
            )  # this is returning multiple results because of the way I was generating test cases based on timestamp

            # print(f"The dynamoIDs are: {dynamoIDs}")
            results = [dynamodb_lookup(ID) for ID in dynamoIDs]
            print(f"The reports returned are: {results}")

            # updates = [update_report(ID) for ID in dynamoIDs]
        else:
            print("About to scan dynamo")
            results = dynamo_scan()

        return {"statusCode": 200, "headers": cors, "body": json.dumps(results)}

    except Exception as e:
        print(e)
        return {"statusCode": 500, "headers": cors, "body": json.dumps("Backend error")}
