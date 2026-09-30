from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routes import router

app = FastAPI(
    title="FitBuddy - AI Fitness Plan Generator"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "FitBuddy is running"}

