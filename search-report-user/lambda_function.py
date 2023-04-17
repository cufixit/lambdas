import json


def lambda_handler(event, context):
    print(f"Received event: {event}")

    report_id = None
    if path_params := event["pathParameters"]:
        report_id = path_params.get("reportId")
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]

    if report_id:
        # Check if report belongs to user
        if False:
            return {
                "statusCode": 403,
                "body": json.dumps("You do not have access to this report"),
            }
        print(f"Fetching report {report_id} for user {user_id}")
    else:
        print(f"Fetching all reports for user {user_id}")

    headers = {
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    }

    return {
        "statusCode": 200,
        "headers": headers,
        "body": json.dumps(event),
    }
