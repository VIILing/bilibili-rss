import re
from fastapi import FastAPI, APIRouter, Request, Response

from my_log import logging, get_logger
from cache_proxy import AbsCacheProxy, MemoryCacheProxy


RSS_CONTENT_CACHE_TIME_S = int(60 * 5)  # todo: read setting instead hard coding
_CacheProxy: AbsCacheProxy = MemoryCacheProxy()
_Logger = get_logger('Main')


_App = FastAPI()


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

