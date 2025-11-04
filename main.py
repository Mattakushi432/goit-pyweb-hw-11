from fastapi import FastAPI
from app.router_contacts import router as contacts_router
from app.router_auth import router as auth_router # Імпортуємо новий роутер

app = FastAPI(
    title="Contacts API",
    description="API для управління телефонною книгою",
    version="1.0.0"
)

app.include_router(auth_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to Contacts API!"}