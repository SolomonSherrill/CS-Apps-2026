from fastapi import FastAPI
from user_auth import user_auth
from pydantic import BaseModel
app = FastAPI()

class AuthRequest(BaseModel):
    username: str
    password: str

auth = user_auth()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/register")
def register(request: AuthRequest):
    return auth.create_user(request.username, request.password)

@app.post("/login")
def login(request: AuthRequest):
    return auth.authenticate_user(request.username, request.password)