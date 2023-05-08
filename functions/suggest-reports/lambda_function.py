import os
import re
import json
import boto3
from botocore.exceptions import ClientError
from formatters import format_report, DataSource
from opensearch import opensearch

AWS_REGION = os.environ["AWS_REGION"]
REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
DOMAIN_ENDPOINT = os.environ["DOMAIN_ENDPOINT"]
DOMAIN_PORT = os.environ.get("DOMAIN_PORT", 443)

DEFAULT_SIZE = 10

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}

dynamodb = boto3.resource("dynamodb")
search = opensearch(AWS_REGION, DOMAIN_ENDPOINT, DOMAIN_PORT)


def normalize(text):
    return re.sub("[^0-9a-zA-Z]+", " ", text)


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        groupID = event["pathParameters"].get("groupId")
        print(f"Retrieving similar reports for group {groupID} ...")

        reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
        response = reports_table.get_item(Key={"ID": groupID})
        print(f"Successfully retrieved group: {response}")

        if not (item := response.get("Item")):
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps(f"Group {groupID} not found"),
            }

        title_query = normalize(item["title"])
        description_query = normalize(item["description"])

        query_fields = [
            "title^4",
            "keywords^2",
            "photoLabels^2",
            "building",
            "description",
        ]
        response = search.search(
            index="reports",
            body={
                "size": DEFAULT_SIZE,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"building": item["building"]}},
                            {
                                "query_string": {
                                    "query": title_query,
                                    "fields": query_fields,
                                    "boost": 4,
                                }
                            },
                            {
                                "query_string": {
                                    "query": description_query,
                                    "fields": query_fields,
                                    "boost": 1,
                                }
                            },
                        ],
                        "should": [
                            {
                                "multi_match": {
                                    "query": title_query,
                                    "fields": query_fields,
                                    "boost": 4,
                                }
                            }
                        ],
                        "must_not": [{"exists": {"field": "groupID"}}],
                    }
                },
            },
        )
        print(f"Successfully retrieved reports from OpenSearch: {response}")

        total = response["hits"]["total"]["value"]
        suggested_reports = [
            format_report(hit["_source"], DataSource.OPENSEARCH, True)
            for hit in response["hits"]["hits"]
            if "_source" in hit
        ]

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {
                    "total": total,
                    "reports": suggested_reports,
                }
            ),
        }

    except ClientError as error:
        print(error)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps("An error occurred while suggesting reports"),
        }
