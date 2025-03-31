import os
import uuid

import boto3
import hmac
import hashlib
import base64

from botocore.exceptions import ClientError

from APIRegistry import APIRouteRegistry, APIRequestException, APIServerException

USER_POOL_ID = os.getenv("USER_POOL_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
client = boto3.client('cognito-idp')
router = APIRouteRegistry()


def get_secret_hash(username):
    msg = username + CLIENT_ID
    dig = hmac.new(str(CLIENT_SECRET).encode('utf-8'),
                   msg=str(msg).encode('utf-8'), digestmod=hashlib.sha256).digest()
    d2 = base64.b64encode(dig).decode()
    return d2

@router.register_route(methods=["POST"], path="/users/sign-up")
def sign_up(event, headers, request):
    for field in ["username", "email", "password",]:
        if not event.get(field):
            return {"error": False, "success": True, 'message': f"{field} is not present", "data": None}
    username = event['username']
    email = event["email"]
    password = event['password']
    return client.sign_up(
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


@router.register_route(methods=["POST"], path="/users/confirm-sign-up")
def confirm_signup(event, headers, request):
    username = event['username']
    code = event['code']
    return client.confirm_sign_up(
        ClientId=CLIENT_ID,
        SecretHash=get_secret_hash(username),
        Username=username,
        ConfirmationCode=code,
        ForceAliasCreation=False,
    )

@router.register_route(methods=["POST"], path="/users/resend-verification-code")
def resend_verification(event, headers, request):
    username = event['username']
    return client.resend_confirmation_code(
        ClientId=CLIENT_ID,
        SecretHash=get_secret_hash(username),
        Username=username,
    )

@router.register_route(methods=["POST"], path="/users/forgot-password")
def forgot_password(event, headers, request):
    username = event['username']
    return client.forgot_password(
        ClientId=CLIENT_ID,
        SecretHash=get_secret_hash(username),
        Username=username,

    )

@router.register_route(methods=["POST"], path="/users/confirm-forgot-password")
def confirm_forgot_password(event, headers, request):
    username = event['username']
    password = event['password']
    code = event['code']
    return client.confirm_forgot_password(
        ClientId=CLIENT_ID,
        SecretHash=get_secret_hash(username),
        Username=username,
        ConfirmationCode=code,
        Password=password,
    )

@router.register_route(methods=["POST"], path="/users/login")
def login(event, headers, request):
    
    for field in ["username", "password"]:
        if event.get(field) is None:
            return {"error": True,
                    "success": False,
                    "message": f"{field} is required",
                    "data": None}

    secret_hash = get_secret_hash(event["username"])
    print("Loggin in...")
    return client.admin_initiate_auth(
        UserPoolId=USER_POOL_ID,
        ClientId=CLIENT_ID,
        AuthFlow='ADMIN_USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': event["username"],
            'SECRET_HASH': secret_hash,
            'PASSWORD': event["password"],
        })



@router.register_route(methods=["POST"], path="/users/forgot")
def get_user(event, headers, request):
    return client.get_user(AccessToken=event["AccessToken"])

@router.register_route(methods=["POST"], path="/users/logout")
def logout(event, headers, request):
    return client.revoke_token(
        Token=event["RefreshToken"],
        ClientId=CLIENT_ID,
        ClientSecret=CLIENT_SECRET
    )

@router.register_route(methods=["POST"], path="/users/refresh-token")
def refresh_login(event, headers, request):
    secret_hash = get_secret_hash(event["username"])
    return client.admin_initiate_auth(
        UserPoolId=USER_POOL_ID,
        ClientId=CLIENT_ID,
        AuthFlow='REFRESH_TOKEN_AUTH',
        AuthParameters={
            'REFRESH_TOKEN': event["RefreshToken"],
            'SECRET_HASH': secret_hash,
        })

# if __name__ == "__main__":
    # print(router.routes)
    # print(sign_up({"username":"", "email":"@gmail.com", "password":""}))
    # print(confirm_signup({"username":"", "code": ""}))
    # print(login({"username":"@gmail.com", "password":""}))
    # print(get_user({"AccessToken":""}))
    # print(logout({"RefreshToken": ""}))
    # print(refresh_login({"username":"","RefreshToken": ""}))


def handle_request(event, context):
    try:
        return router.serve(event, context)
    except ClientError as err:
        raise APIRequestException(err.response["Error"]["Code"],
            err.response["Error"]["Message"])

    except Exception as e:
        raise APIServerException(uuid.uuid4().__str__(), e)
