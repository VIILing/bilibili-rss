from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Response
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler

from my_log import get_logger
from collect_api import auth as auth_api
from collect_api import dynamic as dynamic_collect_api
from convert_api import dynamic as dynamic_convert_api
from cache_proxy import AbsCacheProxy, MemoryCacheProxy


RSS_CONTENT_CACHE_TIME_S = int(60 * 5)  # todo: read setting instead hard coding
cache_proxy: AbsCacheProxy = MemoryCacheProxy()
logger = get_logger('Main')


def update_bilibili_cookie_job():
    logger.info('Start update cookie.')
    fetch_result = auth_api.update()
    if fetch_result.ok:
        logger.info('Successfully update cookie.')
        bili_ticket, img_key, sub_key, buvid3, buvid4 = fetch_result.data
        cache_proxy.set('bili_ticket', bili_ticket)
        cache_proxy.set('img_key', img_key)
        cache_proxy.set('sub_key', sub_key)
        cache_proxy.set('buvid3', buvid3)
        cache_proxy.set('buvid4', buvid4)
    else:
        logger.warn('Update cookie failed.')


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # file_wd = os.path.split(os.path.abspath(__file__))[0]
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_bilibili_cookie_job, CronTrigger(hour=1), id="job_id", name="My periodic task")
    scheduler.start()
    update_bilibili_cookie_job()
    yield
    scheduler.pause()


app = FastAPI(lifespan=lifespan)


StrOrNoneType = str | None


def get_cookie() -> tuple[bool, StrOrNoneType, StrOrNoneType, StrOrNoneType, StrOrNoneType, StrOrNoneType]:
    bili_ticket: bytes | None = cache_proxy.get('bili_ticket')
    img_key: bytes | None = cache_proxy.get('img_key')
    sub_key: bytes | None = cache_proxy.get('sub_key')
    buvid3: bytes | None = cache_proxy.get('buvid3')
    buvid4: bytes | None = cache_proxy.get('buvid4')

    bili_ticket = bili_ticket.decode('utf-8') if bili_ticket is not None else None
    img_key = img_key.decode('utf-8') if img_key is not None else None
    sub_key = sub_key.decode('utf-8') if sub_key is not None else None
    buvid3 = buvid3.decode('utf-8') if buvid3 is not None else None
    buvid4 = buvid4.decode('utf-8') if buvid4 is not None else None

    all_ok = all([e is not None for e in (bili_ticket, img_key, sub_key, buvid3, buvid4)])

    return all_ok, bili_ticket, img_key, sub_key, buvid3, buvid4


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/bilibili/dynamic/{user_id}")
async def bili_dynamic(user_id: int):
    logger.debug(f'Accept dynamic request, user id: {user_id}')
    all_ok, bili_ticket, img_key, sub_key, buvid3, buvid4 = get_cookie()

    if all_ok is False:
        return Response(status_code=500)

    key = f'/bilibili/dynamic/{user_id}'
    cache = cache_proxy.get(key)
    if cache is not None:
        logger.debug(f'Return cache to dynamic request, user id: {user_id}')
        return Response(content=cache.decode('utf-8'), media_type="application/xml")

    logger.debug(f'Get cookie done, send dynamic request, user id: {user_id}')
    async with httpx.AsyncClient() as client:
        fetch_result = await dynamic_collect_api.get_space_data(client, bili_ticket, buvid3, buvid4, img_key, sub_key, user_id)
        if fetch_result.ok is False:
            return Response(500)

    logger.debug(f'Get dynamic data done, start parse, user id: {user_id}')
    feed = dynamic_convert_api.extract_dynamic(user_id, fetch_result.data)
    content = feed.xml()
    cache_proxy.set(key, content, ex=RSS_CONTENT_CACHE_TIME_S)

    logger.debug(f'Return dynamic data, user id: {user_id}')
    return Response(content=content, media_type="application/xml")
