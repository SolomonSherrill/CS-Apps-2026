from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from user_auth import user_auth
from inventory import inventory
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://inventory-manager-frontend-nine.vercel.app"],  # your Vercel URL
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthRequest(BaseModel):
    username: str
    password: str

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

auth = user_auth()
inv = inventory()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/register")
def register(request: AuthRequest):
    return auth.create_user(request.username, request.password)

@app.post("/login")
def login(request: AuthRequest):
    return auth.authenticate_user(request.username, request.password)

@app.get("/inventory/getall")
def get_inventory():
    return inv.get_inventory()

@app.post("/inventory/add")
def add_part(request: AddPartRequest):
    return inv.add_part(request.name, request.category, request.vendor, request.quantity, request.min_quantity, request.part_number, request.url, request.notes)

@app.post("/inventory/update")
def update_inventory(request: UpdateRequest):
    return inv.update_inventory(request.id, request.quantity)