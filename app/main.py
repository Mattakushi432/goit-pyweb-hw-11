import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter

from app.config import settings
from app.router_contacts import router as contacts_router
from app.router_auth import router as auth_router


app = FastAPI(
    title="Contacts API",
    description="API для управління телефонною книгою",
    version="1.0.0"
)


origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    if os.getenv("DISABLE_RATE_LIMITER") == "1":
        # Skip Redis/FastAPILimiter initialization in tests or when explicitly disabled
        return
    r = await redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        encoding="utf-8",
        decode_responses=True
    )

    await FastAPILimiter.init(r)


app.include_router(auth_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to Contacts API!"}
