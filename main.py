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
        "verification_requested": False,
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
            "verification_requested": False,
            "member_since": datetime.now().strftime("%B %Y")
        }
    else:
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

@app.post("/api/v1/me/request-verification")
async def request_verification(token: str):
    for u in users_db.values():
        if u["token"] == token:
            u["verification_requested"] = True
            return {"status": "requested"}
    raise HTTPException(status_code=401, detail="Unauthorized")

# --- MARKETPLACE ENDPOINTS ---
@app.post("/api/v1/products")
async def create_product(token: str, prod: Product):
    user = await get_me(token)
    new_prod = prod.dict()
    new_prod["id"] = len(products_db) + 1
    new_prod["seller_name"] = user["full_name"]
    new_prod["seller_email"] = user["email"]
    new_prod["phone_number"] = user.get("phone_number") or "0245641480"
    new_prod["seller_profile_picture"] = user.get("profile_picture")
    new_prod["seller_verified"] = user.get("is_verified", False)
    new_prod["seller_member_since"] = user.get("member_since", "September 2026")
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

# --- MARKET INTEL (20 REALISTIC GHANAIAN COMMODITIES) ---
@app.get("/api/v1/market-intel")
async def get_intel():
    return [
        {"category": "Live Broilers (2.5kg)", "national_avg": "145.00", "cheapest_region": "Bono East (Techiman)", "cheapest_price": "115.00", "highest_region": "Greater Accra (Accra)", "highest_price": "175.00"},
        {"category": "White Maize (50kg Bag)", "national_avg": "320.00", "cheapest_region": "Northern (Tamale)", "cheapest_price": "260.00", "highest_region": "Ashanti (Kumasi)", "highest_price": "360.00"},
        {"category": "Fresh Eggs (Large Crate)", "national_avg": "65.00", "cheapest_region": "Eastern (Koforidua)", "cheapest_price": "52.00", "highest_region": "Greater Accra (Tema)", "highest_price": "75.00"},
        {"category": "Fresh Tomatoes (Navrongo Crate)", "national_avg": "850.00", "cheapest_region": "Upper East (Navrongo)", "cheapest_price": "620.00", "highest_region": "Greater Accra (Makola)", "highest_price": "1100.00"},
        {"category": "Pona Yam (100 Tubers)", "national_avg": "1400.00", "cheapest_region": "Oti (Nkwanta)", "cheapest_price": "950.00", "highest_region": "Central (Cape Coast)", "highest_price": "1750.00"},
        {"category": "Cassava (Maxi Bag)", "national_avg": "210.00", "cheapest_region": "Volta (Ho)", "cheapest_price": "150.00", "highest_region": "Greater Accra (Madina)", "highest_price": "280.00"},
        {"category": "Farmed Catfish (1kg)", "national_avg": "48.00", "cheapest_region": "Eastern (Asutsuare)", "cheapest_price": "38.00", "highest_region": "Greater Accra (Spintex)", "highest_price": "60.00"},
        {"category": "Soya Beans (50kg Bag)", "national_avg": "420.00", "cheapest_region": "Upper West (Wa)", "cheapest_price": "340.00", "highest_region": "Ashanti (Ejura)", "highest_price": "470.00"},
        {"category": "Plantain (Large Bunch)", "national_avg": "80.00", "cheapest_region": "Western North (Sefwi)", "cheapest_price": "50.00", "highest_region": "Greater Accra (Agbogbloshie)", "highest_price": "120.00"},
        {"category": "Sorghum (50kg Bag)", "national_avg": "250.00", "cheapest_region": "Upper East (Bolgatanga)", "cheapest_price": "190.00", "highest_region": "Greater Accra (Accra)", "highest_price": "310.00"},
        {"category": "Local Rice (50kg Bag)", "national_avg": "500.00", "cheapest_region": "Volta (Aveyime)", "cheapest_price": "420.00", "highest_region": "Greater Accra (Madina)", "highest_price": "560.00"},
        {"category": "Onions (Maxi Bag)", "national_avg": "1200.00", "cheapest_region": "Upper East (Bawku)", "cheapest_price": "850.00", "highest_region": "Greater Accra (Agbogbloshie)", "highest_price": "1500.00"},
        {"category": "Groundnuts (Maxi Bag)", "national_avg": "950.00", "cheapest_region": "Northern (Tamale)", "cheapest_price": "750.00", "highest_region": "Ashanti (Kumasi)", "highest_price": "1100.00"},
        {"category": "Palm Oil (25L Jerrycan)", "national_avg": "400.00", "cheapest_region": "Eastern (Kade)", "cheapest_price": "320.00", "highest_region": "Greater Accra (Tema)", "highest_price": "480.00"},
        {"category": "Tilapia (1kg)", "national_avg": "45.00", "cheapest_region": "Volta (Akosombo)", "cheapest_price": "35.00", "highest_region": "Ashanti (Kumasi)", "highest_price": "55.00"},
        {"category": "Cassava Dough (Maxi Bag)", "national_avg": "150.00", "cheapest_region": "Central (Mankessim)", "cheapest_price": "110.00", "highest_region": "Greater Accra (Kasoa)", "highest_price": "190.00"},
        {"category": "Cabbage (Maxi Sack)", "national_avg": "350.00", "cheapest_region": "Eastern (Aburi)", "cheapest_price": "250.00", "highest_region": "Greater Accra (Madina)", "highest_price": "450.00"},
        {"category": "Pineapple (Dozen)", "national_avg": "60.00", "cheapest_region": "Central (Ekumfi)", "cheapest_price": "40.00", "highest_region": "Greater Accra (Osu)", "highest_price": "80.00"},
        {"category": "Chili Pepper (Maxi Sack)", "national_avg": "800.00", "cheapest_region": "Volta (Denu)", "cheapest_price": "600.00", "highest_region": "Ashanti (Kumasi)", "highest_price": "1000.00"},
        {"category": "Live Goat (Medium)", "national_avg": "900.00", "cheapest_region": "Northern (Yendi)", "cheapest_price": "650.00", "highest_region": "Greater Accra (Accra)", "highest_price": "1200.00"}
    ]

# --- GRANTS (20 VERIFIED AGRICULTURAL FUNDING OPPORTUNITIES) ---
@app.get("/api/v1/grants")
async def get_grants():
    return [
        {"provider": "USAID", "title": "Ghana Trade and Investment Activity", "amount": "$5,000 - $50,000", "deadline": "October 2026", "link": "https://www.usaid.gov/ghana"},
        {"provider": "MoFA", "title": "Planting for Food and Jobs (Phase II)", "amount": "Subsidized Inputs & Seeds", "deadline": "Rolling (Open)", "link": "https://mofa.gov.gh"},
        {"provider": "GIRSAL", "title": "Agribusiness Credit Guarantee Scheme", "amount": "Up to 70% Loan De-risking", "deadline": "Quarterly Intake", "link": "https://girsal.com"},
        {"provider": "KIC Ghana", "title": "AgriTech Challenge Pro 2026", "amount": "$10,000 - $50,000 Equity-free", "deadline": "November 2026", "link": "https://kicghana.org"},
        {"provider": "Mastercard Foundation", "title": "Young Africa Works Agribusiness Fund", "amount": "GH₵ 25,000 - GH₵ 150,000", "deadline": "December 2026", "link": "https://mastercardfdn.org"},
        {"provider": "Exim Bank Ghana", "title": "Export Agricultural Development Facility", "amount": "Low-interest Working Capital", "deadline": "Rolling Intake", "link": "https://www.eximbankghana.com"},
        {"provider": "AfDB", "title": "Incentive-Based Risk Sharing for Ag Lending", "amount": "$20,000 - $100,000", "deadline": "January 2027", "link": "https://www.afdb.org"},
        {"provider": "GCAP", "title": "Commercial Agriculture Project Grants", "amount": "Matching Grants for Irrigation", "deadline": "Rolling", "link": "https://mofa.gov.gh"},
        {"provider": "AGRA", "title": "Sustain Africa Initiative", "amount": "Seed Capital & Inputs", "deadline": "December 2026", "link": "https://agra.org"},
        {"provider": "SNV Ghana", "title": "GrEEn Project Incubation", "amount": "Up to €25,000", "deadline": "November 2026", "link": "https://snv.org/country/ghana"},
        {"provider": "UNDP Ghana", "title": "Agri-Innovation Seed Fund", "amount": "$10,000 Fixed", "deadline": "February 2027", "link": "https://www.gh.undp.org"},
        {"provider": "GEPA & FDA", "title": "Export Readiness Packaging Grant", "amount": "Technical & Material Support", "deadline": "Rolling Intake", "link": "https://www.gepaghana.org"},
        {"provider": "Tony Elumelu Foundation", "title": "TEF Agribusiness Cohort", "amount": "$5,000 Seed Capital", "deadline": "March 2027", "link": "https://www.tonyelumelufoundation.org"},
        {"provider": "IFAD", "title": "Rural Enterprise Programme (REP)", "amount": "Processing Equipment Grants", "deadline": "Rolling", "link": "https://www.ifad.org"},
        {"provider": "GIZ", "title": "AgriBiz Technical Support & Grant", "amount": "Equipment & €15,000", "deadline": "October 2026", "link": "https://www.giz.de/en/worldwide/324.html"},
        {"provider": "Stanbic Bank", "title": "Youth in Agribusiness Incubator", "amount": "GH₵ 50,000 Loan/Grant Mix", "deadline": "December 2026", "link": "https://www.stanbicbank.com.gh"},
        {"provider": "World Food Programme", "title": "Zero Hunger Tech Fund", "amount": "Post-Harvest Tech Grants", "deadline": "January 2027", "link": "https://www.wfp.org"},
        {"provider": "Root Capital", "title": "Agricultural Resilience Loan", "amount": "$50,000 - $2 Million", "deadline": "Rolling Intake", "link": "https://rootcapital.org"},
        {"provider": "Danida", "title": "Ghana Climate Smart Agriculture", "amount": "Matching Capital Grants", "deadline": "February 2027", "link": "https://ghana.um.dk"},
        {"provider": "FAO", "title": "Women in Agro-Processing Fund", "amount": "Capacity Building & Small Grants", "deadline": "November 2026", "link": "https://www.fao.org/ghana"}
    ]

# --- ADMIN ENDPOINTS ---
def require_admin(token: str):
    for u in users_db.values():
        if u["token"] == token and u["email"] == ADMIN_EMAIL:
            return True
    raise HTTPException(status_code=403, detail="Admin access required")

@app.get("/api/v1/admin/verifications")
async def admin_verifications(token: str):
    require_admin(token)
    return [{"name": u["full_name"], "email": u["email"]} for u in users_db.values() if u.get("verification_requested") and not u["is_verified"]]

@app.post("/api/v1/admin/verify")
async def admin_verify_user(req: dict, token: str):
    require_admin(token)
    email = req.get("email")
    if email in users_db:
        users_db[email]["is_verified"] = True
        users_db[email]["verification_requested"] = False
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
    target_id = str(req.get("ad_id"))
    for p in products_db:
        if str(p["id"]) == target_id:
            p["status"] = "approved"
            return {"status": "approved"}
    raise HTTPException(status_code=404, detail="Ad not found")

@app.post("/api/v1/admin/reject-ad")
async def admin_reject_ad(req: dict):
    require_admin(req.get("token"))
    target_id = str(req.get("ad_id"))
    for p in products_db:
        if str(p["id"]) == target_id:
            p["status"] = "rejected"
            p["rejection_reason"] = req.get("reason", "Violated terms")
            return {"status": "rejected"}
    raise HTTPException(status_code=404, detail="Ad not found")

@app.delete("/api/v1/admin/products/{ad_id}")
async def admin_del_ad(token: str, ad_id: int):
    require_admin(token)
    global products_db
    products_db = [p for p in products_db if str(p["id"]) != str(ad_id)]
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
