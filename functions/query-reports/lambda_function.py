import os
import json
from apigateway_helper import cors_headers, AuthContext
from formatters import format_report, DataSource
from opensearch import opensearch

AWS_REGION = os.environ["AWS_REGION"]
DOMAIN_ENDPOINT = os.environ["DOMAIN_ENDPOINT"]
DOMAIN_PORT = os.environ.get("DOMAIN_PORT", 443)
USER_POOL_ID = os.environ["USER_POOL_ID"]
ADMIN_POOL_ID = os.environ["ADMIN_POOL_ID"]

DEFAULT_SIZE = 20
MAX_SIZE = 25


def allow_methods(auth_context):
    if auth_context.is_admin:
        return "GET,OPTIONS"
    return "GET,POST,OPTIONS"


search = opensearch(AWS_REGION, DOMAIN_ENDPOINT, DOMAIN_PORT)


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        auth_context = AuthContext(event, ADMIN_POOL_ID, USER_POOL_ID)

        params = p if (p := event.get("queryStringParameters")) else {}
        print(f"Retrieving reports with query params {params} ...")

        user_id, only_ungrouped = None, False
        if auth_context.is_admin:
            user_id = params.get("userId")
            only_ungrouped = params.get("ungrouped", "false").lower() == "true"

        reports = get_filtered_reports(
            auth_context,
            page_from=params.get("from"),
            page_size=params.get("size"),
            query=params.get("q"),
            user_id=user_id,
            building=params.get("building"),
            status=params.get("status"),
            only_ungrouped=only_ungrouped,
        )

        return {
            "statusCode": 200,
            "headers": cors_headers(allow_methods(auth_context)),
            "body": json.dumps(
                {
                    "reports": reports,
                }
            ),
        }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": cors_headers("OPTIONS"),
            "body": json.dumps(f"Internal server error"),
        }


def get_filtered_reports(
    auth_context,
    page_from=None,
    page_size=None,
    query=None,
    user_id=None,
    building=None,
    status=None,
    only_ungrouped=False,
):
    page_from = 0 if page_from is None else max(0, int(page_from))
    page_size = (
        DEFAULT_SIZE if page_size is None else min(MAX_SIZE, max(1, int(page_size)))
    )

    must_clauses = []
    if not auth_context.is_admin:
        must_clauses.append({"term": {"userID": auth_context.user_id}})
    elif user_id:
        must_clauses.append({"term": {"userID": user_id}})
    if building:
        must_clauses.append({"term": {"building": building}})
    if status:
        must_clauses.append({"term": {"status": status}})

    must_not_clauses = []
    if only_ungrouped:
        must_not_clauses.append({"exists": {"field": "groupID"}})

    should_clauses = []
    if query:
        should_clauses.append(
            {
                "query_string": {
                    "query": query,
                    "fields": [
                        "title^4",
                        "keywords^4",
                        "photoLabels^2",
                        "building^2",
                        "description",
                    ],
                }
            }
        )

    response = search.search(
        index="reports",
        body={
            "from": page_from if page_from else 0,
            "size": page_size if page_size else DEFAULT_SIZE,
            "query": {
                "bool": {
                    "must": must_clauses,
                    "must_not": must_not_clauses,
                    "should": should_clauses,
                }
            },
        },
    )
    print(f"Successfully queried reports: {response}")
    return [
        format_report(hit["_source"], DataSource.OPENSEARCH, auth_context.is_admin)
        for hit in response["hits"]["hits"]
    ]
