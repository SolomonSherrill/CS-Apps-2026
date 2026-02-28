from fastapi import FastAPI
from user_auth import user_auth
from inventory import inventory
from pydantic import BaseModel

app = FastAPI()

class AuthRequest(BaseModel):
    username: str
    password: str

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

@app.get("/inventory/get")
def get_inventory():
    return inv.get_inventory()

@app.get("/inventory/low")
def low_inventory():
    return inv.get_low_inventory()

@app.post("/inventory/update")
def update_inventory(id: int, quantity: int):
    return inv.update_inventory(id, quantity)