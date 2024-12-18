import os
import importlib
from init import get_app, register_all, get_logger


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
