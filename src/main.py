import os
import importlib
from cache_proxy import CacheLib
from init import get_app, register_all, get_logger, get_cache_proxy

from pydantic import BaseModel, Field


logger = get_logger('', root=True)


routes_dir = os.path.join(os.path.dirname(__file__), 'routes')

for root, dirs, files in os.walk(routes_dir):
    for dir_name in dirs:
        main_file = os.path.join(root, dir_name, 'main.py')
        if os.path.exists(main_file) is False:
            logger.warning(f"Can't found main file in package {os.path.join(root, dir_name)}")
            continue
        if os.path.isfile(main_file) is False:
            logger.warning(f"Load point main.py is a folder, not file. Path: {os.path.join(root, dir_name, main_file)}")
            continue
        module_name = f"routes.{dir_name}.main"
        importlib.import_module(module_name)
        logger.info(f"Successfully imported {module_name}")


app = get_app()
register_all()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/api/setting/kv/list")
async def kv_list():
    data = get_cache_proxy().list_all(lib=CacheLib.CONFIG)
    return {
        "status": 0,
        "msg": "",
        "data": {"items": [{'key': k, 'value': v} for k, v in data], "total": len(data)}
    }


class KvUpdate(BaseModel):
    key: str
    value: str


@app.post("/api/setting/kv/update")
async def kv_update(body: KvUpdate):
    get_cache_proxy().set(body.key, body.value)
    return {"status": 0, "msg": ""}
