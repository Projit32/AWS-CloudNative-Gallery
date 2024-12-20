import base64
import functools
import json
import traceback
import uuid

class DuplicateRouteException(ValueError):
    pass

class _APIException(Exception):
    def __init__(self, title, error_code, message, status_code):
        super().__init__('{0} [{1}] -- {2}.'.format(title, error_code, message))
        self.error_code = error_code
        self.message = message
        self.status_code = status_code

class APIRequestException(_APIException):
    def __init__(self, error_code, message):
        super().__init__('API Request Exception', error_code,  message, 400)

class APIResourceNotFoundException(_APIException):
    def __init__(self, error_code, message):
        super().__init__('API Resource Not Found Exception', error_code,  message, 404)

class APIForbiddenAccessException(_APIException):
    def __init__(self, error_code, message):
        super().__init__('API Forbidden Access Exception', error_code,  message, 403)

class APIUnauthorisedAccessException(_APIException):
    def __init__(self, error_code, message):
        super().__init__('API Unauthorized Access Exception', error_code,  message, 401)

class APIServerException(_APIException):
    def __init__(self, error_code, message):
        super().__init__('API Server Exception', error_code,  message, 500)

class APIRouteRegistry:
    routes = {}

    @classmethod
    def register_route(cls, *, methods:list[str] = ["GET"], path: str):
        methods = [method.upper() for method in methods]
        def decorator(func):
            @functools.wraps(func)
            def func_wrap(*args, **kwargs):
                for method in methods:
                    if method not in cls.routes.keys():
                        cls.routes[method] = dict()

                    if path not in cls.routes.get(method).keys():
                        cls.routes.get(method)[path] = func
                    else:
                        raise DuplicateRouteException("Route ["+method+" - "+path+"] already has an assigned function "+func.__name__)

                return func
            return func_wrap()
        return decorator

    @classmethod
    def serve(cls, event:dict, contex:dict) -> dict:
        try:
            body = event.get("body")
            if body and event.get("isBase64Encoded"):
                body = base64.b64decode(body)
            if cls.routes.get(event["httpMethod"]).get(event["path"]):
                response = cls.routes.get(event["httpMethod"]).get(event["path"])(json.loads(body), event)
            else:
                raise APIResourceNotFoundException("Resource "+event["httpMethod"]+" - "+event["path"]+" is not a registered route", uuid.uuid4())
            return {
                    "statusCode": 200,
                    "isBase64Encoded": False,
                    "headers": {
                        "Content-Type": "text/json; charset=utf-8"
                        },
                    "body": json.dumps(response)
                    }
        except _APIException as e:
            traceback.print_exc()
            return {
                "statusCode": e.status_code,
                "isBase64Encoded": False,
                "headers": {
                    "Content-Type": "text/json; charset=utf-8"
                },
                "body": json.dumps({"message": str(e.message), "code": e.error_code})
            }
        except Exception as e:
            traceback.print_exc()
            return {
                "statusCode": 500,
                "isBase64Encoded": False,
                "headers": {
                    "Content-Type": "text/json; charset=utf-8"
                },
                "body": json.dumps({"message": str(e), "code":uuid.uuid4().__str__()})
            }


