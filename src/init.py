import re
import secrets
from typing import Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from pydantic_settings import BaseSettings as EnvSettingModel
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.background import BackgroundScheduler

from my_log import logging, get_or_create_logger
from cache_proxy import AbsCacheProxy, SQLiteCacheProxy


class EnvSetting(EnvSettingModel):
    auth_user: str | None = Field(None, pattern=r'[a-zA-Z0-9]{1,50}')
    auth_pwd: str | None = Field(None, pattern=r'[a-zA-Z0-9!@#$%^&*()-_]{1,50}')


UserEnvSetting = EnvSetting()
_CacheProxy: AbsCacheProxy = SQLiteCacheProxy()
_Logger = get_or_create_logger('Main')


_Security = HTTPBasic()
_AuthUser = None if UserEnvSetting.auth_user is None else UserEnvSetting.auth_user.encode()
_AuthPwd = None if UserEnvSetting.auth_pwd is None else UserEnvSetting.auth_pwd.encode()


if _AuthUser is not None and _AuthPwd is None:
    raise RuntimeError
if _AuthPwd is not None and _AuthUser is None:
    raise RuntimeError


def verify_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(_Security)],
):
    current_username_bytes = credentials.username.encode("utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, _AuthUser
    )
    current_password_bytes = credentials.password.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, _AuthPwd
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def job_clear_expired_cache():
    # todo: This is not a standardized practice, it's not good.
    local_cache_proxy = SQLiteCacheProxy()
    try:
        local_cache_proxy.clear_expired_data()
    finally:
        local_cache_proxy.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(job_clear_expired_cache, IntervalTrigger(minutes=10), id="job_clear_expired_cache", name="job_clear_expired_cache")
    scheduler.start()
    yield
    scheduler.pause()


if _AuthUser is not None:
    _App = FastAPI(dependencies=[Depends(verify_user)], lifespan=lifespan)
else:
    _App = FastAPI(lifespan=lifespan)


_App.mount("/static", StaticFiles(directory="static"), name="static")


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


def get_logger(module_name: str, root: bool = False) -> logging.Logger:
    if root:
        return _Logger
    else:
        assert module_name != ''
        return get_or_create_logger(f'Main.{module_name}')


# def cache_xml_request(cache_time_s: int):
#     def wrapper(func):
#         async def inner(*args, req_obj: Request):
#
#             _Logger.debug(f'key: {req_obj.url.path}')  # this is full path ? (with query)
#             key = req_obj.url.path
#             cache = _CacheProxy.get(key)
#             if cache is not None:
#                 return Response(content=cache, media_type="application/xml")
#
#             resp: Response = await func(*args)
#             body = resp.body
#
#             if cache is not None:
#                 _CacheProxy.set(key, body, ex=cache_time_s)
#
#             return resp
#
#         return inner
#
#     return wrapper
