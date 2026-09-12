from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
import uuid
import base64
import json

app = FastAPI(title="AgromartDirect Backend OS")

# --- CORS SETUP ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- IN-MEMORY MOCK DATABASE ---
users_db = {}
products_db = []
farm_batches_db = []
buyer_requests_db = []
rentals_db = []
waste_db = []
haulage_db = []

# Admin config
ADMIN_EMAIL = "enochdani9@gmail.com"

# --- PYDANTIC MODELS ---
class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    full_name: str
    email: str
    age: int
    phone_number: str
    password: str

class Product(BaseModel):
    product_name: str
    description: str
    category: str
    unit: str
    base_price_ghs: str
    delivery_details: str
    neighborhood: str
    image_data: Optional[str] = None

class FarmBatch(BaseModel):
    batch_name: str
    category: str
    quantity: int
    harvest_days: int

class BuyerRequest(BaseModel):
    item_needed: str
    category: str
    quantity: str
    target_budget_ghs: str
    delivery_destination: str
    description: str

class Rental(BaseModel):
    title: str
    equipment_type: str
    daily_rate_ghs: float
    security_deposit_ghs: float
    location: str

class WasteCollection(BaseModel):
    waste_type: str
    quantity_est: str
    pickup_address: str
    contact_phone: str

# --- AUTH & USER ENDPOINTS ---
@app.post("/api/v1/signup")
async def signup(req: SignupRequest):
    if req.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    token = f"token_{uuid.uuid4().hex}"
    users_db[req.email] = {
        "full_name": req.full_name,
        "email": req.email,
        "phone_number": req.phone_number,
        "age": req.age,
        "password": req.password, 
        "token": token,
        "profile_picture": None,
        "is_verified": False if req.email != ADMIN_EMAIL else True,
        "member_since": datetime.now().strftime("%B %Y")
    }
    return {"access_token": token}

@app.post("/api/v1/login")
async def login(req: LoginRequest):
    user = users_db.get(req.email)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": user["token"]}

@app.post("/api/v1/auth/google")
async def google_auth(req: dict):
    credential = req.get("credential")
    if not credential:
        raise HTTPException(status_code=400, detail="No Google credential provided")
    
    try:
        # Decode the Google JWT payload to extract real user details
        payload_segment = credential.split('.')[1]
        padding = '=' * (4 - len(payload_segment) % 4)
        payload_json = base64.urlsafe_b64decode(payload_segment + padding).decode('utf-8')
        payload = json.loads(payload_json)
        
        email = payload.get("email")
        full_name = payload.get("name", "Farmer")
        picture = payload.get("picture", None)
        
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    token = f"token_{uuid.uuid4().hex}"
    
    if email not in users_db:
        users_db[email] = {
            "full_name": full_name,
            "email": email,
            "phone_number": "",
            "password": "", 
            "token": token,
            "profile_picture": picture,
            "is_verified": True if email == ADMIN_EMAIL else False,
            "member_since": datetime.now().strftime("%B %Y")
        }
    else:
        # Update the session token and picture if the user already exists
        users_db[email]["token"] = token
        if picture:
            users_db[email]["profile_picture"] = picture
            
    return {"access_token": users_db[email]["token"]}

@app.get("/api/v1/me")
async def get_me(token: str):
    for u in users_db.values():
        if u["token"] == token:
            return u
    raise HTTPException(status_code=401, detail="Unauthorized")

@app.put("/api/v1/me/profile-picture")
async def update_profile_pic(token: str, req: dict):
    for u in users_db.values():
        if u["token"] == token:
            u["profile_picture"] = req.get("image_data")
            return {"status": "success"}
    raise HTTPException(status_code=401, detail="Unauthorized")

# --- MARKETPLACE ENDPOINTS ---
@app.post("/api/v1/products")
async def create_product(token: str, prod: Product):
    user = await get_me(token)
    new_prod = prod.dict()
    new_prod["id"] = len(products_db) + 1
    new_prod["seller_name"] = user["full_name"]
    new_prod["seller_email"] = user["email"]
    new_prod["phone_number"] = user["phone_number"]
    new_prod["seller_profile_picture"] = user["profile_picture"]
    new_prod["seller_verified"] = user["is_verified"]
    new_prod["seller_member_since"] = user["member_since"]
    new_prod["status"] = "pending"
    new_prod["boost_tier"] = "standard"
    products_db.append(new_prod)
    return new_prod

@app.get("/api/v1/products")
async def get_products(sort: str = "newest", category: Optional[str] = None, search: Optional[str] = None):
    active_prods = [p for p in products_db if p["status"] == "approved"]
    
    if category:
        active_prods = [p for p in active_prods if p["category"].lower() == category.lower()]
    if search:
        active_prods = [p for p in active_prods if search.lower() in p["product_name"].lower()]
        
    return active_prods

@app.get("/api/v1/my-products")
async def get_my_products(token: str):
    user = await get_me(token)
    return [p for p in products_db if p["seller_email"] == user["email"]]

@app.delete("/api/v1/products/{prod_id}")
async def delete_product(token: str, prod_id: int):
    user = await get_me(token)
    global products_db
    products_db = [p for p in products_db if not (p["id"] == prod_id and p["seller_email"] == user["email"])]
    return {"status": "deleted"}

@app.put("/api/v1/products/{prod_id}")
async def update_product(token: str, prod_id: int, req: dict):
    user = await get_me(token)
    for p in products_db:
        if p["id"] == prod_id and p["seller_email"] == user["email"]:
            p["product_name"] = req.get("product_name", p["product_name"])
            p["base_price_ghs"] = req.get("base_price_ghs", p["base_price_ghs"])
            p["description"] = req.get("description", p["description"])
            return p
    raise HTTPException(status_code=404, detail="Product not found")

# --- FARM MANAGER BATCHES ---
@app.post("/api/v1/farm-batches")
async def create_batch(token: str, batch: FarmBatch):
    user = await get_me(token)
    new_batch = batch.dict()
    new_batch["id"] = len(farm_batches_db) + 1
    new_batch["user_email"] = user["email"]
    new_batch["harvest_date"] = f"In {batch.harvest_days} days"
    new_batch["expenses"] = 0.0
    new_batch["is_ready"] = False
    farm_batches_db.append(new_batch)
    return new_batch

@app.get("/api/v1/farm-batches")
async def get_batches(token: str):
    user = await get_me(token)
    return [b for b in farm_batches_db if b["user_email"] == user["email"]]

# --- BUYER REQUESTS (RFQS) ---
@app.post("/api/v1/buyer-requests")
async def create_rfq(token: str, rfq: BuyerRequest):
    user = await get_me(token)
    new_rfq = rfq.dict()
    new_rfq["id"] = len(buyer_requests_db) + 1
    new_rfq["buyer_email"] = user["email"]
    new_rfq["buyer_phone"] = user["phone_number"]
    new_rfq["created_at"] = datetime.now().strftime("%Y-%m-%d")
    buyer_requests_db.append(new_rfq)
    return new_rfq

@app.get("/api/v1/buyer-requests")
async def get_rfqs():
    return buyer_requests_db

@app.get("/api/v1/my-buyer-requests")
async def get_my_rfqs(token: str):
    user = await get_me(token)
    return [r for r in buyer_requests_db if r["buyer_email"] == user["email"]]

@app.delete("/api/v1/buyer-requests/{rfq_id}")
async def delete_rfq(token: str, rfq_id: int):
    user = await get_me(token)
    global buyer_requests_db
    buyer_requests_db = [r for r in buyer_requests_db if not (r["id"] == rfq_id and r["buyer_email"] == user["email"])]
    return {"status": "deleted"}

# --- RENTALS ---
@app.post("/api/v1/rentals")
async def create_rental(token: str, rental: Rental):
    user = await get_me(token)
    new_rent = rental.dict()
    new_rent["id"] = len(rentals_db) + 1
    new_rent["owner_email"] = user["email"]
    new_rent["owner_name"] = user["full_name"]
    new_rent["owner_phone"] = user["phone_number"]
    rentals_db.append(new_rent)
    return new_rent

@app.get("/api/v1/rentals")
async def get_rentals():
    return rentals_db

@app.get("/api/v1/my-rentals")
async def get_my_rentals(token: str):
    user = await get_me(token)
    return [r for r in rentals_db if r["owner_email"] == user["email"]]

@app.delete("/api/v1/rentals/{rid}")
async def delete_rental(token: str, rid: int):
    user = await get_me(token)
    global rentals_db
    rentals_db = [r for r in rentals_db if not (r["id"] == rid and r["owner_email"] == user["email"])]
    return {"status": "deleted"}

# --- ECO-LOOP (WASTE) ---
@app.post("/api/v1/waste-collections")
async def create_waste(token: str, waste: WasteCollection):
    user = await get_me(token)
    new_waste = waste.dict()
    new_waste["id"] = len(waste_db) + 1
    new_waste["user_email"] = user["email"]
    new_waste["status"] = "Pending Pickup"
    new_waste["address"] = waste.pickup_address
    new_waste["quantity"] = waste.quantity_est
    waste_db.append(new_waste)
    return new_waste

@app.get("/api/v1/waste-collections")
async def get_waste():
    return waste_db

@app.get("/api/v1/my-waste-requests")
async def get_my_waste(token: str):
    user = await get_me(token)
    return [w for w in waste_db if w["user_email"] == user["email"]]

@app.delete("/api/v1/waste-collections/{wid}")
async def delete_waste(token: str, wid: int):
    user = await get_me(token)
    global waste_db
    waste_db = [w for w in waste_db if not (w["id"] == wid and w["user_email"] == user["email"])]
    return {"status": "deleted"}

# --- HAULAGE POOL ---
@app.post("/api/v1/haulage")
async def create_haulage(token: str, req: dict):
    user = await get_me(token)
    new_haul = {
        "id": len(haulage_db) + 1,
        "route": req.get("route"),
        "truck": req.get("truck"),
        "price": req.get("price"),
        "date": req.get("date"),
        "capacity": req.get("capacity"),
        "driver_name": user["full_name"],
        "driver_phone": req.get("driver_phone", user["phone_number"])
    }
    haulage_db.append(new_haul)
    return new_haul

@app.get("/api/v1/haulage")
async def get_haulage():
    return haulage_db

# --- MARKET INTEL (STATIC MOCK FOR NOW) ---
@app.get("/api/v1/market-intel")
async def get_intel():
    return [
        {"category": "Live Broilers", "national_avg": "140.00", "cheapest_region": "Bono East", "cheapest_price": "115.00", "highest_region": "Greater Accra", "highest_price": "165.00"},
        {"category": "Maize (50kg)", "national_avg": "320.00", "cheapest_region": "Northern", "cheapest_price": "280.00", "highest_region": "Ashanti", "highest_price": "360.00"}
    ]

# --- GRANTS (STATIC MOCK FOR NOW) ---
@app.get("/api/v1/grants")
async def get_grants():
    return [
        {"provider": "MoFA", "title": "Planting for Food and Jobs Phase II", "amount": "Subsidized Inputs", "deadline": "Rolling", "link": "https://mofa.gov.gh"},
        {"provider": "USAID", "title": "Ghana Trade and Investment Activity", "amount": "$5,000 - $50,000", "deadline": "October 2026", "link": "#"}
    ]

# --- ADMIN ENDPOINTS ---
def require_admin(token: str):
    for u in users_db.values():
        if u["token"] == token and u["email"] == ADMIN_EMAIL:
            return True
    raise HTTPException(status_code=403, detail="Admin only")

@app.get("/api/v1/admin/pending-users")
async def admin_pending_users(token: str):
    require_admin(token)
    return [{"name": u["full_name"], "email": u["email"]} for u in users_db.values() if not u["is_verified"]]

@app.get("/api/v1/admin/verifications")
async def admin_verifications(token: str):
    require_admin(token)
    return [{"name": u["full_name"], "email": u["email"]} for u in users_db.values() if not u["is_verified"]]

@app.post("/api/v1/admin/verify")
async def admin_verify_user(req: dict, token: str):
    require_admin(token)
    email = req.get("email")
    if email in users_db:
        users_db[email]["is_verified"] = True
        return {"status": "verified"}
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/v1/admin/pending-ads")
async def admin_pending_ads(token: str):
    require_admin(token)
    return [p for p in products_db if p["status"] == "pending"]

@app.get("/api/v1/admin/all-ads")
async def admin_all_ads(token: str):
    require_admin(token)
    return products_db

@app.post("/api/v1/admin/approve-ad")
async def admin_approve_ad(req: dict):
    require_admin(req.get("token"))
    for p in products_db:
        if p["id"] == req.get("ad_id"):
            p["status"] = "approved"
            return {"status": "approved"}
    raise HTTPException(status_code=404, detail="Ad not found")

@app.post("/api/v1/admin/reject-ad")
async def admin_reject_ad(req: dict):
    require_admin(req.get("token"))
    for p in products_db:
        if p["id"] == req.get("ad_id"):
            p["status"] = "rejected"
            p["rejection_reason"] = req.get("reason", "Violated terms")
            return {"status": "rejected"}
    raise HTTPException(status_code=404, detail="Ad not found")

@app.delete("/api/v1/admin/products/{ad_id}")
async def admin_del_ad(token: str, ad_id: int):
    require_admin(token)
    global products_db
    products_db = [p for p in products_db if p["id"] != ad_id]
    return {"status": "deleted"}

@app.post("/api/v1/admin/ban-user")
async def admin_ban_user(req: dict, token: str):
    require_admin(token)
    email = req.get("email")
    if email in users_db:
        del users_db[email]
        global products_db
        products_db = [p for p in products_db if p["seller_email"] != email]
        return {"status": "banned"}
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/v1/admin/reports")
async def admin_get_reports(token: str):
    require_admin(token)
    return []

# --- RECOVERY ---
@app.post("/api/v1/auth/forgot-password")
async def fp_req(req: dict):
    return {"status": "code sent"}

@app.post("/api/v1/auth/reset-password")
async def fp_reset(req: dict):
    phone = req.get("phone_number")
    new_pw = req.get("new_password")
    for u in users_db.values():
        if u["phone_number"] == phone:
            u["password"] = new_pw
            return {"status": "reset"}
    raise HTTPException(status_code=404, detail="Phone not registered")
