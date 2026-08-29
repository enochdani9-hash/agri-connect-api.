import os
from datetime import datetime, timedelta
from typing import Optional, List
import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load local .env file if running locally
load_dotenv()

app = FastAPI(title="AgriConnect Ghana API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# SECURE ENVIRONMENT CONFIGURATION
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://avchhgythvzkwclaebii.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_F85AUjbPax_zuJNm3KCQsA_mqFlK-Ch")
JWT_SECRET = os.getenv("JWT_SECRET", "g8A3eeKYyosRosfenDiuCT8oUwf3YznLRlcrkyAZpaGnkpncOU2n0epl8VDn+r9bdesUVO/oJfHHfXC5svxBVA==")
JWT_ALGORITHM = "HS256"

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================
class UserSignup(BaseModel):
    full_name: str
    email: str
    age: int
    phone_number: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ProductCreate(BaseModel):
    product_name: str
    category: str
    unit: str
    base_price_ghs: str
    neighborhood: str
    description: Optional[str] = ""
    image_data: Optional[str] = None

class AdminVerify(BaseModel):
    email: str

# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================
@app.post("/api/v1/signup")
async def signup(user: UserSignup):
    token = jwt.encode(
        {"email": user.email, "full_name": user.full_name, "exp": datetime.utcnow() + timedelta(days=7)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    return {
        "access_token": token,
        "full_name": user.full_name,
        "email": user.email,
        "is_verified": False
    }

@app.post("/api/v1/login")
async def login(user: UserLogin):
    token = jwt.encode(
        {"email": user.email, "exp": datetime.utcnow() + timedelta(days=7)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    return {
        "access_token": token,
        "full_name": "Farmer",
        "email": user.email,
        "is_verified": (user.email == "enochdani9@gmail.com")
    }

@app.get("/api/v1/me")
async def get_me(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("email")
        full_name = payload.get("full_name", "Farmer")
        is_verified = (email == "enochdani9@gmail.com")
        return {"full_name": full_name, "email": email, "is_verified": is_verified}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")

# ==========================================
# PRODUCT & CLASSIFIEDS ENDPOINTS
# ==========================================
@app.get("/api/v1/products")
async def get_products(sort: str = "newest", category: Optional[str] = None, search: Optional[str] = None, neighborhood: Optional[str] = None):
    return []

@app.get("/api/v1/my-products")
async def get_my_products(token: str):
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return []
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/api/v1/products")
async def create_product(product: ProductCreate, token: str):
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"status": "success", "message": "Ad submitted for review"}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.delete("/api/v1/products/{product_id}")
async def delete_product(product_id: int, token: str):
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"status": "success", "message": "Ad deleted"}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ==========================================
# ADMIN ENDPOINTS
# ==========================================
@app.post("/api/v1/admin/verify")
async def verify_seller(data: AdminVerify, token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("email") != "enochdani9@gmail.com":
            raise HTTPException(status_code=403, detail="Forbidden: Founder access required.")
        return {"detail": f"User {data.email} verified successfully."}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ==========================================
# AUTOMATIONS & NOTIFICATIONS
# ==========================================
async def send_arkesel_sms(phone: str, message: str):
    url = "https://sms.arkesel.com/sms/api"
    payload = {
        "action": "send-sms",
        "api_key": os.getenv("ARKESEL_API_KEY", "YOUR_ARKESEL_KEY"),
        "to": phone,
        "from": "AgriConnect",
        "sms": message
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"SMS Gateway dispatch failed: {e}")

@app.post("/api/v1/notify-farmer")
async def notify_farmer(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    phone = payload.get("phone", "")
    item = payload.get("item", "")
    offer = payload.get("offer", "")
    
    msg = f"AgriConnect: New buyer inquiry received for your {item} (Est. GHc{offer}). Open WhatsApp to reply!"
    background_tasks.add_task(send_arkesel_sms, phone, msg)
    return {"status": "SMS Queued"}

@app.post("/api/v1/paystack-webhook")
async def paystack_webhook(request: Request):
    payload = await request.json()
    if payload.get("event") == "charge.success":
        data = payload.get("data", {})
        metadata = data.get("metadata", {})
        ad_id = metadata.get("ad_id")
        boost_type = metadata.get("boost_type")
        print(f"MoMo Boost Confirmed: Ad {ad_id} boosted with {boost_type}")
    return {"status": "success"}

@app.get("/")
async def root():
    return {"service": "AgriConnect Ghana API", "status": "online"}
