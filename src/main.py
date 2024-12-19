import os
import importlib
import init
from init import get_app, register_all, get_logger, get_cache_proxy

from pydantic import BaseModel, Field


logger = get_logger()


routes_dir = os.path.join(os.path.dirname(__file__), 'routes')

for root, dirs, files in os.walk(routes_dir):
    for dir_name in dirs:
        main_file = os.path.join(root, dir_name, 'main.py')
        if os.path.isfile(main_file):
            module_name = f"routes.{dir_name}.main"
            importlib.import_module(module_name)
            logger.info(f"Successfully imported {module_name}")


app = get_app()
register_all()


@app.get("/")
async def root():
    return {"message": "Hello World"}


class ChangeAuthBody(BaseModel):
    username: str = Field(..., pattern='[a-zA-Z0-9]{1, 50}')
    password: str = Field(..., pattern='[a-zA-Z0-9]{1, 50}')


@app.post("/api/setting/auth/changeAuth")
async def change_auth(change: ChangeAuthBody):
    init.change_auth(username=change.username, password=change.password)
    return {"message": "ok"}


@app.get("/api/setting/kv/list")
async def kv_list():
    data = get_cache_proxy().list_all()
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
