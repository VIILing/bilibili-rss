import os
import importlib
from cache_proxy import CacheLib
from init import get_app, register_all, get_logger, get_cache_proxy

from pydantic import BaseModel
from fastapi.responses import HTMLResponse


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


"""
Home page
"""


@app.get("/")
async def root():
    return {"message": "Hello World"}
                       
                       
"""
Manager web page
"""


with open(os.path.join(os.path.split(__file__)[0], 'resources', 'amis_template.html'), 'r', encoding='utf-8') as _fn:
    AmisTemplate = _fn.read()


PageJsonCache: dict[str, str] = dict()
for _root, _dirs, _files in os.walk(os.path.join(os.path.split(__file__)[0], 'resources', 'pages')):
    for _name in _files:
        with open(os.path.join(_root, _name), 'r', encoding='utf-8') as _fn:
            _json_content = _fn.read()
        PageJsonCache[_name] = _json_content


Custom500ErrorHtml = """
<html>
    <head>
        <title>Server Error</title>
    </head>
    <body>
        <h1>500 - Internal Server Error</h1>
        <p>Something went wrong. Please try again later.</p>
    </body>
</html>
"""


def render_html(json_content: str) -> HTMLResponse:
    return HTMLResponse(content=AmisTemplate.format(json_body=json_content), status_code=200)


@app.get("/web/setting/cookie_manager")
async def web_setting_cookie_manager():
    json_content = PageJsonCache.get("cookie_manager.json")
    if json_content is None:
        return HTMLResponse(content=Custom500ErrorHtml, status_code=500)
    return render_html(json_content)


"""
Manager api
"""


@app.get("/api/setting/cookie/list")
async def kv_list():
    data = get_cache_proxy().list_all(lib=CacheLib.CONFIG)
    return {
        "status": 0,
        "msg": "",
        "data": {"items": [{'key': k, 'value': v} for k, v in data], "total": len(data)}
    }


@app.get("/api/setting/cookie/list2")
async def kv_list_2():
    data = get_cache_proxy().list_all_2(lib=CacheLib.CONFIG)
    items = []
    for k, v, ut, et in data:
        items.append({
            'key': k,
            'value': v,
            'update_time': ut,
            'expired_time': et
        })
    return {
        "status": 0,
        "msg": "",
        "data": {"items": items, "total": len(data)}
    }


class KvUpdate(BaseModel):
    key: str
    value: str


@app.post("/api/setting/cookie/update")
async def kv_update(body: KvUpdate):
    get_cache_proxy().set(body.key, body.value)
    return {"status": 0, "msg": ""}
