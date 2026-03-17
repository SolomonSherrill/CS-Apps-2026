from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
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

class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str

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
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not found in .env")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def create_token(username: str, role: str):
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": username, "role": role, "exp": expire}, SECRET_KEY, algorithm="HS256")

def verify_request(request: Request):
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = auth.split(" ",1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username

def get_role(request: Request):
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = auth.split(" ",1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    role = payload.get("role")
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return role

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/auth/register")
@limiter.limit("1000/hour")
async def register(request: Request, body: AuthRequest):
    return auth.create_user(body.username, body.password, body.invite_code)

@app.post("/auth/login")
@limiter.limit("1000/hour")
async def login(request: Request, body: AuthRequest):
    result = auth.authenticate_user(body.username, body.password)
    if result.get("success"):
        result["token"] = create_token(body.username, result["role"])
    return result

@app.post("/auth/change_password")
@limiter.limit("1000/hour")
def change_password(request: Request, body: ChangePasswordRequest, username: str = Depends(verify_request)):
    if username != body.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return auth.change_password(body.username, body.old_password, body.new_password)

@app.get("/inventory/getall")
def get_inventory(username: str = Depends(verify_request)):
    return inv.get_inventory()

@app.post("/inventory/add")
def add_part(request: AddPartRequest, username: str = Depends(verify_request)):
    return inv.add_part(request.name, request.category, request.vendor, request.quantity, request.min_quantity, request.part_number, request.url, request.notes)

@app.post("/inventory/update")
def update_inventory(request: UpdateRequest, username: str = Depends(verify_request)):
    return inv.update_inventory(request.id, request.quantity)

@app.put("/inventory/edit")
def edit_part(request: EditPartRequest, username: str = Depends(verify_request)):
    return inv.edit_part(request.id, request.name, request.category, request.vendor, request.quantity, request.min_quantity, request.part_number, request.url, request.notes)

@app.delete("/inventory/delete")
def delete_part(id: int, username: str = Depends(verify_request)):
    return inv.delete_part(id)

@app.get("/admin/getusers")
def get_users(username: str = Depends(verify_request), role: str = Depends(get_role)):
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return auth.get_users()