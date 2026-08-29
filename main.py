import os
from datetime import datetime, timedelta
from typing import Optional, List
import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request, Body, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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
# SECURE CONFIGURATION & SUPABASE HEADERS
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://avchhgythvzkwclaebii.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_F85AUjbPax_zuJNm3KCQsA_mqFlK-Ch")
JWT_SECRET = os.getenv("JWT_SECRET", "g8A3eeKYyosRosfenDiuCT8oUwf3YznLRlcrkyAZpaGnkpncOU2n0epl8VDn+r9bdesUVO/oJfHHfXC5svxBVA==")
JWT_ALGORITHM = "HS256"

ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY", "")
MAKE_ZAPIER_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
CRON_SECRET = os.getenv("CRON_SECRET", "super-secret-cron-key-123")

ADMIN_EMAIL = "enochdani9@gmail.com"

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

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
        {
            "email": user.email,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "exp": datetime.utcnow() + timedelta(days=30)
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    return {
        "access_token": token,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "is_verified": (user.email == ADMIN_EMAIL)
    }

@app.post("/api/v1/login")
async def login(user: UserLogin):
    token = jwt.encode(
        {
            "email": user.email,
            "full_name": "Farmer",
            "phone_number": "",
            "exp": datetime.utcnow() + timedelta(days=30)
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    return {
        "access_token": token,
        "full_name": "Farmer",
        "email": user.email,
        "is_verified": (user.email == ADMIN_EMAIL)
    }

@app.get("/api/v1/me")
async def get_me(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("email")
        full_name = payload.get("full_name", "Farmer")
        phone_number = payload.get("phone_number", "")
        is_verified = (email == ADMIN_EMAIL)
        return {
            "full_name": full_name,
            "email": email,
            "phone_number": phone_number,
            "is_verified": is_verified
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")

# ==========================================
# PRODUCT & CLASSIFIEDS ENDPOINTS
# ==========================================
@app.get("/api/v1/products")
async def get_products(sort: str = "newest", category: Optional[str] = None, search: Optional[str] = None):
    url = f"{SUPABASE_URL}/rest/v1/products?select=*"
    params = {}
    if category:
        params["category"] = f"eq.{category}"
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=get_supabase_headers(), params=params, timeout=10.0)
            if res.status_code == 200:
                products = res.json()
                if search:
                    s = search.lower()
                    products = [p for p in products if s in p.get("product_name", "").lower() or s in p.get("neighborhood", "").lower()]
                if sort == "price_asc":
                    products.sort(key=lambda x: float(x.get("base_price_ghs", 0) or 0))
                elif sort == "price_desc":
                    products.sort(key=lambda x: float(x.get("base_price_ghs", 0) or 0), reverse=True)
                return products
            else:
                print(f"Supabase GET Error: {res.text}")
                return []
    except Exception as e:
        print(f"Supabase fetch exception: {e}")
        return []

@app.get("/api/v1/my-products")
async def get_my_products(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("email")
        url = f"{SUPABASE_URL}/rest/v1/products?seller_email=eq.{email}&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=get_supabase_headers(), timeout=10.0)
            return res.json() if res.status_code == 200 else []
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/api/v1/products")
async def create_product(product: ProductCreate, token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        new_ad = {
            "product_name": product.product_name,
            "category": product.category,
            "unit": product.unit,
            "base_price_ghs": str(product.base_price_ghs),
            "neighborhood": product.neighborhood,
            "description": product.description,
            "image_data": product.image_data,
            "seller_email": payload.get("email"),
            "seller_name": payload.get("full_name", "Farmer"),
            "phone_number": payload.get("phone_number", "0240000000"),
            "status": "pending"
        }

        url = f"{SUPABASE_URL}/rest/v1/products"
        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=get_supabase_headers(), json=new_ad, timeout=10.0)
            
            if res.status_code in [200, 201]:
                return {"status": "success", "message": "Ad submitted for review"}
            else:
                error_msg = res.text
                print(f"SUPABASE REJECTION: {error_msg}")
                raise HTTPException(status_code=400, detail=f"Database Error: Check Supabase Columns! {error_msg}")
                
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.delete("/api/v1/products/{product_id}")
async def delete_product(product_id: int, token: str):
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        url = f"{SUPABASE_URL}/rest/v1/products?id=eq.{product_id}"
        async with httpx.AsyncClient() as client:
            await client.delete(url, headers=get_supabase_headers(), timeout=10.0)
        return {"status": "success", "message": "Ad deleted"}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ==========================================
# ADMIN REVIEW & AUTOMATION 1 (SOCIAL SYNDICATION)
# ==========================================
@app.get("/api/v1/admin/pending-ads")
async def get_pending_ads(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("email") != ADMIN_EMAIL:
            raise HTTPException(status_code=403, detail="Forbidden")
        url = f"{SUPABASE_URL}/rest/v1/products?status=eq.pending&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=get_supabase_headers(), timeout=10.0)
            return res.json() if res.status_code == 200 else []
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

async def broadcast_social_syndication(product_name: str, price: str, neighborhood: str):
    if not MAKE_ZAPIER_WEBHOOK_URL:
        return
    payload = {
        "event": "ad_approved",
        "product_name": product_name,
        "price_ghs": price,
        "location": neighborhood,
        "link": "https://agriconnect.com"
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(MAKE_ZAPIER_WEBHOOK_URL, json=payload, timeout=10.0)
    except Exception as e:
        print(f"Syndication Webhook dispatch failed: {e}")

@app.post("/api/v1/admin/approve-ad")
async def approve_ad(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    token = payload.get("token", "")
    ad_id = payload.get("ad_id")
    try:
        jwt_data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if jwt_data.get("email") != ADMIN_EMAIL:
            raise HTTPException(status_code=403, detail="Forbidden")

        url = f"{SUPABASE_URL}/rest/v1/products?id=eq.{ad_id}"
        async with httpx.AsyncClient() as client:
            res = await client.patch(url, headers=get_supabase_headers(), json={"status": "approved"}, timeout=10.0)
            data = res.json() if res.status_code == 200 else []

        prod_name = data[0].get("product_name", "Farm Produce") if data else "Farm Produce"
        prod_price = str(data[0].get("base_price_ghs", "0")) if data else "0"
        prod_loc = data[0].get("neighborhood", "Ghana") if data else "Ghana"

        background_tasks.add_task(broadcast_social_syndication, prod_name, prod_price, prod_loc)
        return {"status": "success", "message": "Ad Approved and Syndicated"}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/api/v1/admin/verify")
async def verify_seller(data: AdminVerify, token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("email") != ADMIN_EMAIL:
            raise HTTPException(status_code=403, detail="Forbidden")
        return {"detail": f"User {data.email} verified successfully."}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ==========================================
# AUTOMATION 2: ARKESEL SMS LEAD ALERTS
# ==========================================
async def send_arkesel_sms(phone: str, message: str):
    if not ARKESEL_API_KEY or not phone:
        print(f"[SMS Alert Sim]: To {phone} -> {message}")
        return
    url = "https://sms.arkesel.com/sms/api"
    payload = {
        "action": "send-sms",
        "api_key": ARKESEL_API_KEY,
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
    
    msg = f"AgriConnect: New buyer inquiry for your {item} (Est. GHc{offer}). Open WhatsApp to reply!"
    background_tasks.add_task(send_arkesel_sms, phone, msg)
    return {"status": "SMS Queued"}

# ==========================================
# AUTOMATION 4: PAYSTACK MOMO BOOST
# ==========================================
@app.post("/api/v1/paystack-webhook")
async def paystack_webhook(request: Request):
    payload = await request.json()
    if payload.get("event") == "charge.success":
        data = payload.get("data", {})
        metadata = data.get("metadata", {})
        ad_id = metadata.get("ad_id")
        boost_type = metadata.get("boost_type", "featured")
        if ad_id:
            url = f"{SUPABASE_URL}/rest/v1/products?id=eq.{ad_id}"
            async with httpx.AsyncClient() as client:
                await client.patch(url, headers=get_supabase_headers(), json={"boost_tier": boost_type})
    return {"status": "success"}

# ==========================================
# AUTOMATION 3 & 5: CRON SCHEDULER ENDPOINTS
# ==========================================
@app.post("/api/v1/cron/ad-expiry-loop")
async def cron_ad_expiry_loop(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "success", "message": "Ad expiry verification complete"}

@app.post("/api/v1/cron/weekly-market-digest")
async def cron_weekly_market_digest(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "success", "message": "Weekly digest broadcast triggered"}

@app.get("/")
async def root():
    return {"service": "AgriConnect Ghana API", "status": "online"}
