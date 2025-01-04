import re
from io import BytesIO
from datetime import datetime
from contextlib import asynccontextmanager, closing

from init import get_router, get_cache_proxy, get_logger

from cache_proxy import CacheLib
from fastapi import APIRouter, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pixivpy3 import AppPixivAPI, PixivError
from . import novel
from rss_model import AtomFeed


RSS_CONTENT_CACHE_TIME_S = int(60 * 5)  # todo: read setting instead hard coding
CacheProxy = get_cache_proxy()
Logger = get_logger('pixiv')


AApi: AppPixivAPI | None = None


def initialize_aapi(refresh_token: str) -> bool:
    Logger.info(f'Start login to pixiv')
    # api = AppPixivAPI(proxies={'http': 'http://127.0.0.1:10809', 'https': 'http://127.0.0.1:10809'})
    api = AppPixivAPI()
    try:
        api.auth(refresh_token=refresh_token)
    except PixivError:
        return False
    global AApi
    AApi = api
    Logger.info('Successfully login to pixiv.')
    return True


@asynccontextmanager
async def lifespan(_app: APIRouter):
    refresh_token = CacheProxy.get('pixiv_refresh_token')
    if refresh_token is None:
        CacheProxy.set('pixiv_refresh_token', '')
    else:
        if refresh_token.decode() == '':
            pass
        else:
            initialize_aapi(refresh_token.decode())
    yield


def check_init():
    if AApi is None:
        refresh_token = CacheProxy.get('pixiv_refresh_token')
        if refresh_token is None or refresh_token.decode() == '':
            raise HTTPException(status_code=400, detail="Not login.")
        else:
            ok = initialize_aapi(refresh_token.decode())
            if ok:
                pass
            else:
                raise HTTPException(status_code=400, detail="Login failed.")
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
        AApi.download(real_path, fname=bio)
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

    author_name, entry_list = novel.user_novels(AApi, user_id, CacheProxy)

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

    Logger.debug(f'Return dynamic data, user id: {user_id}')
    return Response(content=feed.xml(), media_type="application/xml")
