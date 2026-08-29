import os
from datetime import datetime, timedelta
from typing import Optional, List
import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request, Body, BackgroundTasks, Header
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

# Arkesel & Webhook Keys
ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY", "YOUR_ARKESEL_KEY")
MAKE_ZAPIER_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "https://hook.us1.make.com/your-custom-webhook")
CRON_SECRET = os.getenv("CRON_SECRET", "super-secret-cron-key-123") # Used to protect your cron endpoints

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
# ADMIN ENDPOINTS (WITH AUTOMATION 1 TRIGGER)
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

# (AUTOMATION 1) Social Syndication Webhook Triggered on Ad Approval
async def broadcast_social_syndication(product_name: str, price: str, neighborhood: str, image_url: str):
    """Pushes approved ads to Make.com/Zapier for Facebook & WhatsApp Broadcasts"""
    payload = {
        "event": "ad_approved",
        "product_name": product_name,
        "price_ghs": price,
        "location": neighborhood,
        "image": image_url,
        "link": "https://agriconnect.com"
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(MAKE_ZAPIER_WEBHOOK_URL, json=payload, timeout=10.0)
    except Exception as e:
        print(f"Syndication Webhook Failed: {e}")

@app.post("/api/v1/admin/approve-ad")
async def approve_ad(background_tasks: BackgroundTasks, ad_id: int = Body(...), token: str = Body(...)):
    """Admin endpoint to approve an ad and automatically trigger social syndication"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("email") != "enochdani9@gmail.com":
            raise HTTPException(status_code=403, detail="Forbidden.")
        
        # In production, query the DB for the ad details here
        mock_product_name = "Live Broilers"
        mock_price = "150"
        mock_neighborhood = "Accra"
        mock_image = "https://example.com/image.jpg"
        
        # Trigger the social syndication automation in the background
        background_tasks.add_task(broadcast_social_syndication, mock_product_name, mock_price, mock_neighborhood, mock_image)
        
        return {"status": "success", "message": "Ad Approved and Syndicated"}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ==========================================
# (AUTOMATION 2) AUTOMATED SMS LEAD ALERTS
# ==========================================
async def send_arkesel_sms(phone: str, message: str):
    """Sends SMS using Arkesel Gateway"""
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
    """Triggered by the Deal Room on the frontend when a buyer clicks Order"""
    phone = payload.get("phone", "")
    item = payload.get("item", "")
    offer = payload.get("offer", "")
    
    msg = f"AgriConnect: New buyer inquiry received for your {item} (Est. GHc{offer}). Open WhatsApp to reply!"
    background_tasks.add_task(send_arkesel_sms, phone, msg)
    return {"status": "SMS Queued"}

# ==========================================
# (AUTOMATION 4) PAYSTACK MOMO AUTOMATED BOOST ACTIVATION
# ==========================================
@app.post("/api/v1/paystack-webhook")
async def paystack_webhook(request: Request):
    """Listens for Paystack MoMo success events to instantly upgrade ad visibility"""
    payload = await request.json()
    if payload.get("event") == "charge.success":
        data = payload.get("data", {})
        metadata = data.get("metadata", {})
        ad_id = metadata.get("ad_id")
        boost_type = metadata.get("boost_type") # e.g., 'category_highlight' or 'spotlight_badge'
        
        # In production: supabase.table("products").update({"boost_tier": boost_type}).eq("id", ad_id).execute()
        print(f"MoMo Boost Confirmed: Ad {ad_id} boosted with {boost_type}")
    return {"status": "success"}

# ==========================================
# (AUTOMATION 3 & 5) CRON JOB ENDPOINTS
# ==========================================
# These endpoints are built to be triggered by Render Cron Jobs or GitHub Actions on a schedule.

@app.post("/api/v1/cron/ad-expiry-loop")
async def cron_ad_expiry_loop(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Runs daily to check for 30-day old ads and sends WhatsApp/SMS renewal prompts."""
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized Cron Trigger")
    
    # In production: Fetch all ads created < (today - 30 days) where status='active'
    expired_ads_mock = [{"phone": "233540000000", "item": "Day-Old Chicks"}]
    
    for ad in expired_ads_mock:
        msg = f"Your listing for {ad['item']} has expired on AgriConnect. Reply '1' to renew for free or '2' to boost to top."
        # Background dispatch to avoid timeout
        background_tasks.add_task(send_arkesel_sms, ad["phone"], msg)
        
    return {"status": "success", "processed": len(expired_ads_mock)}

@app.post("/api/v1/cron/weekly-market-digest")
async def cron_weekly_market_digest(background_tasks: BackgroundTasks, x_cron_secret: str = Header(None)):
    """Runs every Sunday to aggregate prices and trigger the Digest Webhook/SMS."""
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized Cron Trigger")
    
    # In production: Calculate averages from the DB
    digest_msg = "AgriConnect Weekly Digest: Maize averages GHc200/bag. Broilers average GHc150. Check app for detailed regional trends!"
    
    # Send to Make.com/Zapier webhook to distribute the newsletter/SMS bulk broadcast
    payload = {"event": "weekly_digest", "message": digest_msg}
    
    async def dispatch_digest():
        try:
            async with httpx.AsyncClient() as client:
                await client.post(MAKE_ZAPIER_WEBHOOK_URL, json=payload, timeout=10.0)
        except:
            pass
            
    background_tasks.add_task(dispatch_digest)
    return {"status": "success", "message": "Weekly digest broadcast triggered."}

@app.get("/")
async def root():
    return {"service": "AgriConnect Ghana API", "status": "online"}
