class AuthContext:
    def __init__(self, event, admin_pool_id, user_pool_id):
        authorizer = event["requestContext"]["authorizer"]
        self.pool_id = authorizer["claims"]["iss"].split("/")[-1]
        self.user_id = authorizer["claims"]["sub"]

        if self.pool_id not in [admin_pool_id, user_pool_id]:
            raise Exception("Not authorized to access this resource")
        self.is_admin = self.pool_id == admin_pool_id


def cors_headers(allow_methods, allow_headers="Content-Type", allow_origin="*"):
    return {
        "Access-Control-Allow-Headers": allow_headers,
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": allow_methods,
    }
