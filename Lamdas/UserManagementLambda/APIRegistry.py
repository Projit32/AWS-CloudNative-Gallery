import base64
import functools
import traceback

from Exceptions import DuplicateRouteException

class ApiRouteRegistry:
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
            return cls.routes.get(event["httpMethod"]).get(event["path"])(body, event)
        except Exception as e:
            traceback.print_exc()
            print(e)