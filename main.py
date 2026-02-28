from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from datetime import datetime, timedelta
from user_auth import user_auth
from inventory import inventory
from pydantic import BaseModel
from typing import Optional
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthRequest(BaseModel):
    username: str
    password: str
    invite_code: Optional[str] = None

class AddPartRequest(BaseModel):
    name: str
    category: str
    vendor: str
    quantity: int
    min_quantity: int
    part_number: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None

class UpdateRequest(BaseModel):
    id: int
    quantity: int

class EditPartRequest(BaseModel):
    id: int
    name: Optional[str] = None
    category: Optional[str] = None
    vendor: Optional[str] = None
    quantity: Optional[int] = None
    min_quantity: Optional[int] = None
    part_number: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None

auth = user_auth()
inv = inventory()
SECRET_KEY = os.getenv("SECRET_KEY")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def create_token(username: str):
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm="HS256")

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/register")
@limiter.limit("1/minute")
async def register(request: Request, body: AuthRequest):
    return auth.create_user(body.username, body.password, body.invite_code)

@app.post("/login")
@limiter.limit("20/minute")
async def login(request: Request, body: AuthRequest):
    result = auth.authenticate_user(body.username, body.password)
    if result.get("success"):
        result["token"] = create_token(body.username)
    return result

@app.get("/inventory/getall")
def get_inventory():
    return inv.get_inventory()

@app.post("/inventory/add")
def add_part(request: AddPartRequest):
    return inv.add_part(request.name, request.category, request.vendor, request.quantity, request.min_quantity, request.part_number, request.url, request.notes)

@app.post("/inventory/update")
def update_inventory(request: UpdateRequest):
    return inv.update_inventory(request.id, request.quantity)

@app.post("/inventory/edit")
def edit_part(request: EditPartRequest):
    return inv.edit_part(request.id, request.name, request.category, request.vendor, request.quantity, request.min_quantity, request.part_number, request.url, request.notes)

@app.delete("/inventory/delete")
def delete_part(id: int):
    return inv.delete_part(id)