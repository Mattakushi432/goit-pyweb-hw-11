from fastapi import FastAPI
from app.router import router as contacts_router

app = FastAPI(
    title="Contacts API",
    description="API для управления телефонной книгой",
    version="1.0.0"
)


app.include_router(contacts_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to Contacts API!"}