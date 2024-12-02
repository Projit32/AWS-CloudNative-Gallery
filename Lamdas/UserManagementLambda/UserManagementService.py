import traceback

import boto3
import botocore.exceptions
import hmac
import hashlib
import base64
import json
from APIRegistry import ApiRouteRegistry

USER_POOL_ID = ''
CLIENT_ID = ''
CLIENT_SECRET = ''
client = boto3.client('cognito-idp')
router = ApiRouteRegistry()


def get_secret_hash(username):
    msg = username + CLIENT_ID
    dig = hmac.new(str(CLIENT_SECRET).encode('utf-8'),
                   msg=str(msg).encode('utf-8'), digestmod=hashlib.sha256).digest()
    d2 = base64.b64encode(dig).decode()
    return d2

@router.register_route(methods=["POST"], path="/users/sign-up")
def sign_up(event, request):
    for field in ["username", "email", "password",]:
        if not event.get(field):
            return {"error": False, "success": True, 'message': f"{field} is not present", "data": None}
    username = event['username']
    email = event["email"]
    password = event['password']
    
    try:
        resp = client.sign_up(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(username),
            Username=username,
            Password=password,
            UserAttributes=[
                {
                    'Name': "email",
                    'Value': email
                }
            ])


    except client.exceptions.UsernameExistsException as e:
        return {"error": False,
                "success": True,
                "message": "This username already exists",
                "data": None}
    except client.exceptions.InvalidPasswordException as e:

        return {"error": False,
                "success": True,
                "message": "Password should have Caps,\
                          Special chars, Numbers",
                "data": None}
    except client.exceptions.UserLambdaValidationException as e:
        return {"error": False,
                "success": True,
                "message": "Email already exists",
                "data": None}

    except Exception as e:
        return {"error": False,
                "success": True,
                "message": str(e),
                "data": None}

    return {"error": False,
            "success": True,
            "message": "Please confirm your signup, \
                        check Email for validation code",
            "data": None}

@router.register_route(methods=["POST"], path="/users/confirm-sign-up")
def confirm_signup(event, request):
    
    try:
        username = event['username']
        code = event['code']
        response = client.confirm_sign_up(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(username),
            Username=username,
            ConfirmationCode=code,
            ForceAliasCreation=False,
        )
    except client.exceptions.UserNotFoundException:
        # return {"error": True, "success": False, "message": "Username doesnt exists"}
        return event
    except client.exceptions.CodeMismatchException:
        return {"error": True, "success": False, "message": "Invalid Verification code"}

    except client.exceptions.NotAuthorizedException:
        return {"error": True, "success": False, "message": "User is already confirmed"}

    except Exception as e:
        return {"error": True, "success": False, "message": f"Unknown error {e.__str__()} "}

    return event

@router.register_route(methods=["POST"], path="/users/resend-verification-code")
def resend_verification(event, request):
    
    try:
        username = event['username']
        response = client.resend_confirmation_code(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(username),
            Username=username,
        )
    except client.exceptions.UserNotFoundException:
        return {"error": True, "success": False, "message": "Username doesnt exists"}

    except client.exceptions.InvalidParameterException:
        return {"error": True, "success": False, "message": "User is already confirmed"}

    except Exception as e:
        return {"error": True, "success": False, "message": f"Unknown error {e.__str__()} "}

    return {"error": False, "success": True}

@router.register_route(methods=["POST"], path="/users/forgot-password")
def forgot_password(event, request):
    
    try:
        username = event['username']
        response = client.forgot_password(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(username),
            Username=username,

        )
    except client.exceptions.UserNotFoundException:
        return {"error": True,
                "data": None,
                "success": False,
                "message": "Username doesnt exists"}

    except client.exceptions.InvalidParameterException:
        return {"error": True,
                "success": False,
                "data": None,
                "message": f"User <{username}> is not confirmed yet"}

    except client.exceptions.CodeMismatchException:
        return {"error": True,
                "success": False,
                "data": None,
                "message": "Invalid Verification code"}

    except client.exceptions.NotAuthorizedException:
        return {"error": True,
                "success": False,
                "data": None,
                "message": "User is already confirmed"}

    except Exception as e:
        return {"error": True,
                "success": False,
                "data": None,
                "message": f"Uknown    error {e.__str__()} "}

    return {
        "error": False,
        "success": True,
        "message": f"Please check your Registered email id for validation code",
        "data": None}

@router.register_route(methods=["POST"], path="/users/confirm-forgot-password")
def confirm_forgot_password(event, request):
    
    try:
        username = event['username']
        password = event['password']
        code = event['code']
        client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(username),
            Username=username,
            ConfirmationCode=code,
            Password=password,
        )
    except client.exceptions.UserNotFoundException as e:
        return {"error": True,
                "success": False,
                "data": None,
                "message": "Username doesnt exists"}

    except client.exceptions.CodeMismatchException as e:
        return {"error": True,
            "success": False,
            "data": None,
            "message": "Invalid Verification code"}

    except client.exceptions.NotAuthorizedException as e:
        return {"error": True,
            "success": False,
            "data": None,
            "message": "User is already confirmed"}

    except Exception as e:
        return {"error": True,
            "success": False,
            "data": None,
            "message": f"Unknown error {e.__str__()} "}

    return {"error": False,
            "success": True,
            "message": f"Password has been changed successfully",
            "data": None}

@router.register_route(methods=["POST"], path="/users/initiate-auth")
def initiate_auth(client, username, password):
    secret_hash = get_secret_hash(username)
    try:
      resp = client.admin_initiate_auth(
                 UserPoolId=USER_POOL_ID,
                 ClientId=CLIENT_ID,
                 AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                 AuthParameters={
                     'USERNAME': username,
                    'SECRET_HASH': secret_hash,
                     'PASSWORD': password,
                  })
    except client.exceptions.NotAuthorizedException:
        return None, "The username or password is incorrect"
    except client.exceptions.UserNotConfirmedException:
        return None, "User is not confirmed"
    except Exception as e:
        return None, e.__str__()
    return resp, None

@router.register_route(methods=["POST"], path="/users/login")
def login(event, request):
    
    for field in ["username", "password"]:
        if event.get(field) is None:
            return {"error": True,
                    "success": False,
                    "message": f"{field} is required",
                    "data": None}
    resp, msg = initiate_auth(client, event["username"], event["password"])
    if msg != None:
        return {'message': msg,
                "error": True, "success": False, "data": None}
    if resp.get("AuthenticationResult"):
        return {'message': "success",
                "error": False,
                "success": True,
                "data": resp
                }
    else:  # this code block is relevant only when MFA is enabled
        return {"error": True,
                "success": False,
                "data": None, "message": None}


@router.register_route(methods=["POST"], path="/users/forgot")
def get_user(event, request):
    return client.get_user(AccessToken=event["AccessToken"])

def logout(event, request):
    return client.revoke_token(
        Token=event["RefreshToken"],
        ClientId=CLIENT_ID,
        ClientSecret=CLIENT_SECRET
    )

@router.register_route(methods=["POST"], path="/users/refresh-token")
def refresh_login(event, request):
    secret_hash = get_secret_hash(event["username"])
    try:
        resp = client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': event["RefreshToken"],
                'SECRET_HASH': secret_hash,
            })
    except client.exceptions.NotAuthorizedException as e:
        print(e)
        return None, "The username or password is incorrect"
    except client.exceptions.UserNotConfirmedException:
        return None, "User is not confirmed"
    except Exception as e:
        return None, e.__str__()
    return resp, None

if __name__ == "__main__":
    print(router.routes)
    #print(sign_up({"username":"", "email":"@gmail.com", "password":""}))
    # print(confirm_signup({"username":"", "code": ""}))
    # print(login({"username":"@gmail.com", "password":""}))
    # print(get_user({"AccessToken":""}))
    # print(logout({"RefreshToken": ""}))
    # print(refresh_login({"username":"","RefreshToken": ""}))


def handle_request(event, context):
    return router.serve(event, context)
