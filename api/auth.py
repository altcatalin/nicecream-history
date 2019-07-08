import base64
import json
from functools import wraps
from http import HTTPStatus

import aiohttp
import hashlib
import os
from typing import Union, Callable
from urllib.parse import urlencode

from aiohttp import web
from aiohttp_session import get_session

from api.database import fetch_user_by_sub, insert_user, update_user
from api.logger import get_logger
from api.settings import settings

log = get_logger(__name__)


def private_path(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(request: web.Request, **kwargs) -> Union[Callable,  web.Response]:
        session = await get_session(request)

        if "user_id" not in session:
            raise web.HTTPUnauthorized()

        return await handler(request, **kwargs)
    return wrapper


async def generate_google_authorization_url(request: web.Request) -> str:
    session = await get_session(request)
    session["oauth2_state"] = hashlib.sha256(os.urandom(1024)).hexdigest()
    g_settings = settings["oauth2"]["google"]

    params = {
        "scope": "email profile",
        "response_type": "code",
        "redirect_uri": g_settings["redirect_url"],
        "client_id": g_settings["client_id"],
        "state": session["oauth2_state"],
        "prompt": "select_account"
    }

    authorization_url = f"{g_settings['authorization_endpoint']}?{urlencode(params)}"
    return authorization_url


async def exchange_google_code_for_tokens(request: web.Request) -> None:
    session = await get_session(request)
    database = request.app["database"]
    g_settings = settings["oauth2"]["google"]

    if "oauth2_state" not in session \
            or "state" not in request.query \
            or session["oauth2_state"] != request.query["state"]:
        log.error("Cannot confirm anti-forgery state token")
    elif "code" not in request.query:
        log.error("Cannot extract authorization code")
    else:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }

        payload = {
            "code": request.query["code"],
            "client_id": g_settings["client_id"],
            "client_secret": g_settings["client_secret"],
            "redirect_uri": g_settings["redirect_url"],
            "grant_type": "authorization_code"
        }

        async with aiohttp.ClientSession() as client_session:
            async with client_session.post(g_settings["token_endpoint"], data=payload, headers=headers) as response:
                if not response.status == HTTPStatus.OK:
                    log.error("Cannot exchange authorization code")
                else:
                    data = await response.json()
                    id_token = data["id_token"].encode("utf-8")
                    encoded_header, encoded_payload, signature = id_token.split(b'.')
                    encoded_payload = encoded_payload + b'=' * (-len(encoded_payload) % 4)
                    decoded_payload = base64.urlsafe_b64decode(encoded_payload)
                    payload = json.loads(decoded_payload.decode("utf-8"))

                    user = await fetch_user_by_sub(database, payload["sub"])

                    if user:
                        user_id = user["id"]
                        await update_user(database,
                                          payload["given_name"], payload["family_name"],
                                          payload["picture"])
                    else:
                        user_id = await insert_user(database,
                                                    payload["sub"],
                                                    payload["given_name"], payload["family_name"],
                                                    payload["picture"])

                    session["user_id"] = user_id
