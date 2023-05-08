import os
import json
from formatters import format_group, DataSource
from opensearch import opensearch

AWS_REGION = os.environ["AWS_REGION"]
DOMAIN_ENDPOINT = os.environ["DOMAIN_ENDPOINT"]
DOMAIN_PORT = os.environ.get("DOMAIN_PORT", 443)

DEFAULT_SIZE = 20
MAX_SIZE = 25

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}

search = opensearch(AWS_REGION, DOMAIN_ENDPOINT, DOMAIN_PORT)


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        params = p if (p := event.get("queryStringParameters")) else {}
        print(f"Retrieving groups with query params {params} ...")

        results = get_filtered_groups(
            page_from=params.get("from"),
            page_size=params.get("size"),
            query=params.get("q"),
            building=params.get("building"),
            status=params.get("status"),
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(results),
        }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps(f"Internal server error"),
        }


def get_filtered_groups(
    page_from=None, page_size=None, query=None, building=None, status=None
):
    page_from = 0 if page_from is None else max(0, int(page_from))
    page_size = (
        DEFAULT_SIZE if page_size is None else min(MAX_SIZE, max(1, int(page_size)))
    )

    must_clauses = []
    if building:
        must_clauses.append({"term": {"building": building}})
    if status:
        must_clauses.append({"term": {"status": status}})

    should_clauses = []
    if query:
        should_clauses.append(
            {
                "query_string": {
                    "query": query,
                    "fields": [
                        "title^4",
                        "building^2",
                        "description",
                    ],
                }
            }
        )

    response = search.search(
        index="groups",
        body={
            "from": page_from if page_from else 0,
            "size": page_size if page_size else 20,
            "query": {"bool": {"must": must_clauses, "should": should_clauses}},
        },
    )
    print(f"Successfully queried groups: {response}")
    total = response["hits"]["total"]["value"]
    groups = [
        format_group(hit["_source"], DataSource.OPENSEARCH)
        for hit in response["hits"]["hits"]
    ]
    return {"total": total, "groups": groups}
