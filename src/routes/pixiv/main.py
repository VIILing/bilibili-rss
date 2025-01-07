import re
from io import BytesIO
from datetime import datetime
from contextlib import asynccontextmanager, closing

from init import get_router, get_cache_proxy, get_logger

from cache_proxy import CacheLib
from fastapi import APIRouter, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse
from . import novel
from .base import get_aapi, update_aapi, FetchError
from rss_model import AtomFeed


RSS_CONTENT_CACHE_TIME_S = int(60 * 5)  # todo: read setting instead hard coding
CacheProxy = get_cache_proxy()
Logger = get_logger('pixiv')


@asynccontextmanager
async def lifespan(_app: APIRouter):
    update_aapi(Logger, CacheProxy)
    yield


def check_init():
    aapi = get_aapi()
    if aapi is None:
        refresh_token = CacheProxy.get('pixiv_refresh_token')
        if refresh_token is None or refresh_token == b'':
            raise HTTPException(status_code=400, detail="Not login.")
        else:
            aapi = update_aapi(Logger, CacheProxy)
            if aapi is None:
                raise HTTPException(status_code=400, detail="Login failed.")
            else:
                pass
    else:
        pass


router = get_router('pixiv', lifespan=lifespan, dependencies=[Depends(check_init)])


@router.get("/img_proxy/{full_path:path}")
async def image_proxy(full_path: str):
    img_type = re.findall(r'\.(jpg|png|jpeg|wbep).*$', full_path)
    if img_type is None or len(img_type) == 0 or img_type[0] not in {'jpg', 'png', 'jpeg', 'wbep'}:
        return Response(status_code=404)
    img_type = img_type[0]

    key = f'/rss/pixiv/img_proxy/{full_path}'
    cache = CacheProxy.get(key)
    if cache is not None:
        Logger.debug(f'Return cache to request, key: {key}')
        return Response(content=cache, media_type=f"image/{img_type}")

    real_path = full_path.replace('https---', 'https://').replace('http---', 'http://')
    bio: BytesIO
    with closing(BytesIO()) as bio:
        get_aapi().download(real_path, fname=bio)
        bio.seek(0)
        bc = bio.getvalue()
    CacheProxy.set(key, bc, lib=CacheLib.RUNTIME)
    return Response(content=bc, media_type=f"image/{img_type}")


@router.get('/novel_redirect/{novel_id}')
async def novel_redirect(novel_id: str):
    return RedirectResponse(url=f'https://www.pixiv.net/novel/show.php?id={novel_id}')


@router.get("/user_novels/{user_id}")
async def user_novels(user_id: int):
    Logger.debug(f'Accept user_novels request, user id: {user_id}')

    key = f'/rss/pixiv/user_novels/{user_id}'
    cache = CacheProxy.get(key)
    if cache is not None:
        Logger.debug(f'Return cache to request, key: {key}')
        return Response(content=cache.decode('utf-8'), media_type="application/xml")

    try:
        author_name, entry_list = novel.user_novels(get_aapi(), user_id, CacheProxy)
    except FetchError:
        return HTTPException(status_code=500, detail="Fetch failed, maybe token expired or network error.")

    Logger.debug(f'Fetch user novel data done, user id: {user_id}')

    feed = AtomFeed(
        title=f'{author_name}的 Pixiv 小说列表',
        link=f'/rss/pixiv/user_novels/{user_id}',
        updated=datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        authors=[author_name],
        fid=f'brss/pixiv/user_novels/{user_id}',
        entry_list=entry_list
    )
    CacheProxy.set(key, feed.xml(), ex=RSS_CONTENT_CACHE_TIME_S, lib=CacheLib.RUNTIME)

    Logger.debug(f"Return pixiv user's novel data, user id: {user_id}")
    return Response(content=feed.xml(), media_type="application/xml")
