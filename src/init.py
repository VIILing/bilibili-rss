import re
import secrets
from typing import Annotated
from fastapi import FastAPI, APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from my_log import logging, get_logger
from cache_proxy import AbsCacheProxy, MemoryCacheProxy


_CacheProxy: AbsCacheProxy = MemoryCacheProxy()
_Logger = get_logger('Main')


_Security = HTTPBasic()
_AUTH_USER: bytes | None = None
_AUTH_PWD: bytes | None = None


if _AUTH_USER is not None:
    if type(_AUTH_USER) is not str or _AUTH_PWD is None or type(_AUTH_PWD) is not bytes:
        raise RuntimeError


def verify_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(_Security)],
):
    if _AUTH_USER is None:
        return ""

    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = _AUTH_USER
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = _AUTH_PWD
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


_App = FastAPI(dependencies=[Depends(verify_user)])


def get_app() -> FastAPI:
    return _App


_ApiRouterList = []


def get_router(domain: str, **kwargs) -> APIRouter:
    if re.match(r'[a-zA-Z0-9-_}{]+', domain) is None:
        raise RuntimeError(f'Invalid domain: {domain}')
    if 'prefix' in kwargs:
        del kwargs['prefix']
    if 'tags' in kwargs:
        if type(kwargs['tags']) is not list:
            raise TypeError('Type of variable tags is not list')
        if domain not in kwargs['tags']:
            kwargs['tags'].append(domain)
    else:
        kwargs['tags'] = [domain]
    router = APIRouter(prefix=f'/rss/{domain}', **kwargs)
    _ApiRouterList.append(router)
    return router


def register_all():
    for router in _ApiRouterList:
        _App.include_router(router)


def get_cache_proxy() -> AbsCacheProxy:
    return _CacheProxy


def get_logger() -> logging.Logger:
    return _Logger


def cache_request(cache_time_s: int):
    def wrapper(func):
        async def inner(*args, req_obj: Request):

            _Logger.debug(f'key: {req_obj.url.path}')  # this is full path ? (with query)
            key = req_obj.url.path
            cache = _CacheProxy.get(key)
            if cache is not None:
                return Response(content=cache.decode('utf-8'), media_type="application/xml")

            feed = await func(*args)
            content = feed.xml()

            if cache is not None:
                _CacheProxy.set(key, content, ex=cache_time_s)

            return Response(content=content, media_type="application/xml")

        return inner

    return wrapper

