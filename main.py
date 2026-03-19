#used to define the API endpoints for user authentication and inventory management, as well as the necessary request models and utility functions for token creation and verification
from fastapi import FastAPI, Request, Depends, HTTPException, status
#used to allow requests from any origin
from fastapi.middleware.cors import CORSMiddleware
#used to save user tokens and verify them
from jose import jwt, JWTError
#used to assign token expiry times
from datetime import datetime, timedelta
#importing methods from my other files
from user_auth import user_auth
from inventory import inventory
#request models for specific methods
from pydantic import BaseModel
#used in requests for when a parameter is optional
from typing import Optional
import os
#used to ratelimit requests to prevent abuse, not really limited currently
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

#used to connect to my database and use python to execute sql queries, also includes methods for user authentication and inventory management
app = FastAPI()
#allows requests from any origin for testing purposes, can be restricted in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#request to login or register a user, requires username and password, and an optional invite code for registration
class AuthRequest(BaseModel):
    username: str
    password: str
    invite_code: Optional[str] = None

#request to unlock a user's account, requires the username of the account to be unlocked, admin role required to access this endpoint
class UnlockRequest(BaseModel):
    username: str

#request to change a user's password, requires the username, old password for verification, and new password, user must be authenticated and can only change their own password
class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str

#request to add a part to the inventory, requires name, category, vendor, quantity, and minimum quantity, with optional parameters for part number, url, and notes, user must be authenticated to access this endpoint
class AddPartRequest(BaseModel):
    name: str
    category: str
    vendor: str
    quantity: int
    min_quantity: int
    part_number: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None

#request to update the quantity of a part in the inventory, requires the part id and new quantity, user must be authenticated to access this endpoint
class UpdateRequest(BaseModel):
    id: int
    quantity: int

#request to edit a part in the inventory, requires the part id and any parameters to be updated, user must be authenticated to access this endpoint
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

#initializes the user_auth and inventory classes, which handle database interactions for user authentication and inventory management respectively, also loads the secret key for token creation from environment variables
auth = user_auth()
inv = inventory()

#loads the secret key for token creation from environment variables, raises an error if not found
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not found in .env")

#initializes the rate limiter for the API, currently set to allow 1000 requests per hour for each endpoint, can be adjusted as needed
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

#function to create a JWT token for a user upon successful authentication, includes the username, role, and expiry time in the token payload
def create_token(username: str, role: str):
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": username, "role": role, "exp": expire}, SECRET_KEY, algorithm="HS256")

#function to verify the JWT token included in the Authorization header of requests, extracts the username from the token payload if valid, raises an error if the token is missing or invalid
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

#returns role of user making a request, used to restrict access to admin-only endpoints, raises an error if the token is missing or invalid
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

#method to check if api is running
@app.get("/")
def root():
    return {"status": "ok"}

#api endpoint to register a new user
@app.post("/auth/register")
@limiter.limit("1000/hour")
async def register(request: Request, body: AuthRequest):
    return auth.create_user(body.username, body.password, body.invite_code)

#api endpoint to login a user, returns a JWT token if authentication is successful, which can be included in the Authorization header of subsequent requests to access admin-only endpoints
@app.post("/auth/login")
@limiter.limit("1000/hour")
async def login(request: Request, body: AuthRequest):
    result = auth.authenticate_user(body.username, body.password)
    if result.get("success"):
        result["token"] = create_token(body.username, result["role"])
    return result

#api endpoint for a user to change their password, users can only change their own password
@app.post("/auth/change_password")
@limiter.limit("1000/hour")
def change_password(request: Request, body: ChangePasswordRequest, username: str = Depends(verify_request)):
    if username != body.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return auth.change_password(body.username, body.old_password, body.new_password)

#api endpoint to retrieve entire inventory, reqiuires authentication
@app.get("/inventory/getall")
def get_inventory(username: str = Depends(verify_request)):
    return inv.get_inventory()

#api endpoint to add a part to the inventory, requires authentication
@app.post("/inventory/add")
def add_part(request: AddPartRequest, username: str = Depends(verify_request)):
    return inv.add_part(request.name, request.category, request.vendor, request.quantity, request.min_quantity, request.part_number, request.url, request.notes)

#api endpoint to update the quantity of a part in the inventory, requires authentication
@app.post("/inventory/update")
def update_inventory(request: UpdateRequest, username: str = Depends(verify_request)):
    return inv.update_inventory(request.id, request.quantity)

#api endpoint to edit a part in the inventory, requires authentication
@app.put("/inventory/edit")
def edit_part(request: EditPartRequest, username: str = Depends(verify_request)):
    return inv.edit_part(request.id, request.name, request.category, request.vendor, request.quantity, request.min_quantity, request.part_number, request.url, request.notes)

#api endpoint to delete a part from the inventory, requires authentication
@app.delete("/inventory/delete")
def delete_part(id: int, username: str = Depends(verify_request)):
    return inv.delete_part(id)

#api endpoint to retrieve a list of all users, their roles, and lockout status, requires admin role to access
@app.get("/admin/getusers")
def get_users(username: str = Depends(verify_request), role: str = Depends(get_role)):
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return auth.get_users()

#api endpoint to unlock a user's account by resetting failed attempts and lockout status, requires admin role to access
@app.post("/admin/unlock_user")
def unlock_user(request: UnlockRequest, username: str = Depends(verify_request), role: str = Depends(get_role)):
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return auth.unlock_user(request.username)