from threading import Lock
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


update_lock = Lock()
cache_proxy: AbsCacheProxy = MemoryCacheProxy()
logger = get_logger('Main')


def update_bilibili_cookie_job():
    fetch_result = auth_api.update()
    if fetch_result.ok:
        bili_ticket, img_key, sub_key, buvid3, buvid4 = fetch_result.data
        update_lock.acquire()
        cache_proxy.set('bili_ticket', bili_ticket)
        cache_proxy.set('img_key', img_key)
        cache_proxy.set('sub_key', sub_key)
        cache_proxy.set('buvid3', buvid3)
        cache_proxy.set('buvid4', buvid4)
        update_lock.release()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # file_wd = os.path.split(os.path.abspath(__file__))[0]
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_bilibili_cookie_job, CronTrigger(hour=1), id="job_id", name="My periodic task")
    scheduler.start()
    logger.debug('开始更新cookie')
    update_bilibili_cookie_job()
    logger.debug('更新cookie结束')
    yield
    scheduler.pause()


app = FastAPI(lifespan=lifespan)


StrOrNoneType = str | None


def get_cookie() -> tuple[bool, StrOrNoneType, StrOrNoneType, StrOrNoneType, StrOrNoneType, StrOrNoneType]:
    update_lock.acquire()
    bili_ticket: bytes | None = cache_proxy.get('bili_ticket')
    img_key: bytes | None = cache_proxy.get('img_key')
    sub_key: bytes | None = cache_proxy.get('sub_key')
    buvid3: bytes | None = cache_proxy.get('buvid3')
    buvid4: bytes | None = cache_proxy.get('buvid4')
    update_lock.release()

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
async def bili_dynamic(user_id):
    all_ok, bili_ticket, img_key, sub_key, buvid3, buvid4 = get_cookie()

    if all_ok is False:
        return Response(status_code=500)

    async with httpx.AsyncClient() as client:
        fetch_result = await dynamic_collect_api.get_space_data(client, bili_ticket, buvid3, buvid4, img_key, sub_key, user_id)
        if fetch_result.ok is False:
            return Response(500)

    feed = dynamic_convert_api.extract_dynamic(user_id, fetch_result.data)
    return Response(content=feed.xml(), media_type="application/xml")
