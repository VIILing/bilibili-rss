from init import get_app, register_all
from routes.bilibili import bilibili_main  # Use dynamic import instead of manual import in the future


app = get_app()
register_all()


@app.get("/")
async def root():
    return {"message": "Hello World"}
