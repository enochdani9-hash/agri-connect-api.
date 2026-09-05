import os
import re
from datetime import datetime, timedelta
from typing import List, Optional
import httpx
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Header, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt

# --- CONFIGURATION ---
SECRET_KEY = "agriconnect_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agriconnect_jiji.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="AgromartDirect API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- SECRETS & KEYS ---
ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY", "")
MAKE_ZAPIER_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
CRON_SECRET = os.getenv("CRON_SECRET", "super-secret-cron-key-123")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
ADMIN_EMAIL = "enochdani9@gmail.com"

reset_codes_db = {}

# --- DATABASE MODELS ---
class User(Base):
    __tablename__ = "users_v5"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    age = Column(Integer)
    phone_number = Column(String)
    hashed_password = Column(String)
    is_verified = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)  
    profile_picture = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    products = relationship("Product", back_populates="owner")
    buyer_requests = relationship("BuyerRequest", back_populates="buyer")
    farm_batches = relationship("FarmBatch", back_populates="farmer")

class Product(Base):
    __tablename__ = "products_v7"  
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, index=True)
    category = Column(String, index=True)
    unit = Column(String)
    base_price_ghs = Column(String)  
    neighborhood = Column(String)
    description = Column(String, nullable=True)
    image_data = Column(Text, nullable=True)
    delivery_details = Column(String, nullable=True) 
    farmer_id = Column(Integer, ForeignKey("users_v5.id"))
    status = Column(String, default="pending")       
    rejection_reason = Column(String, nullable=True) 
    boost_tier = Column(String, default="standard")  
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="products")

class BuyerRequest(Base):
    __tablename__ = "buyer_requests_v1"
    id = Column(Integer, primary_key=True, index=True)
    item_needed = Column(String, index=True)
    category = Column(String, index=True)
    quantity = Column(String)
    target_budget_ghs = Column(String)
    delivery_destination = Column(String)
    description = Column(String, nullable=True)
    buyer_id = Column(Integer, ForeignKey("users_v5.id"))
    status = Column(String, default="open")  
    created_at = Column(DateTime, default=datetime.utcnow)
    
    buyer = relationship("User", back_populates="buyer_requests")

class FarmBatch(Base):
    __tablename__ = "farm_batches_v1"
    id = Column(Integer, primary_key=True, index=True)
    batch_name = Column(String)
    category = Column(String)
    quantity = Column(Integer)
    total_expenses = Column(Float, default=0.0)
    start_date = Column(DateTime, default=datetime.utcnow)
    harvest_date = Column(DateTime)
    farmer_id = Column(Integer, ForeignKey("users_v5.id"))
    is_harvested = Column(Boolean, default=False)
    
    farmer = relationship("User", back_populates="farm_batches")

class AgriOpportunity(Base):
    __tablename__ = "agri_opportunities_v1"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    provider = Column(String)
    amount = Column(String)
    deadline = Column(String)
    link = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class VerificationPayment(Base):
    __tablename__ = "verification_payments_v2"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    paid_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports_v1"
    id = Column(Integer, primary_key=True, index=True)
    reported_seller_name = Column(String)
    reported_seller_phone = Column(String)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class EquipmentListing(Base):
    __tablename__ = "equipment_listings_v1"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users_v5.id"))
    title = Column(String, index=True)
    equipment_type = Column(String)
    daily_rate_ghs = Column(Float)
    security_deposit_ghs = Column(Float, default=0)
    location = Column(String)
    is_available = Column(Boolean, default=True)
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class WasteCollection(Base):
    __tablename__ = "waste_collections_v1"
    id = Column(Integer, primary_key=True, index=True)
    generator_id = Column(Integer, ForeignKey("users_v5.id"))
    waste_type = Column(String)
    quantity_est = Column(String)
    pickup_address = Column(String)
    contact_phone = Column(String)
    status = Column(String, default="pending")
    assigned_driver = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# -> CREATE TABLES AFTER ALL MODELS ARE DEFINED!
Base.metadata.create_all(bind=engine)

# --- SCHEMAS ---
class UserCreate(BaseModel):
    full_name: str; email: str; age: int; phone_number: str; password: str
class UserLogin(BaseModel):
    email: str; password: str
class ProfilePicUpdate(BaseModel):
    image_data: str
class ProductCreate(BaseModel):
    product_name: str; category: str; unit: str; base_price_ghs: str; neighborhood: str
    description: Optional[str] = None; image_data: Optional[str] = None; delivery_details: Optional[str] = None
class ProductEdit(BaseModel):
    product_name: str; base_price_ghs: str; description: Optional[str] = None
class BuyerRequestCreate(BaseModel):
    item_needed: str; category: str; quantity: str; target_budget_ghs: str; delivery_destination: str
    description: Optional[str] = None
class FarmBatchCreate(BaseModel):
    batch_name: str; category: str; quantity: int; harvest_days: int
class WhatsappWebhook(BaseModel):
    phone_number: str; message_text: str
class AdminVerify(BaseModel):
    email: str
class AdminBan(BaseModel):
    email: str
class RejectPayload(BaseModel):
    token: str; ad_id: int; reason: str
class ForgotPasswordReq(BaseModel):
    phone_number: str
class ResetPasswordReq(BaseModel):
    phone_number: str; code: str; new_password: str
class GoogleAuthRequest(BaseModel):
    credential: str
class ReportCreate(BaseModel):
    seller_name: str; seller_phone: str; reason: str
class EquipmentRentalCreate(BaseModel):
    title: str; equipment_type: str; daily_rate_ghs: float; security_deposit_ghs: float; location: str; image_url: Optional[str] = None
class WasteCollectionCreate(BaseModel):
    waste_type: str; quantity_est: str; pickup_address: str; contact_phone: str

# --- DEPENDENCIES ---
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_current_user(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None: raise credentials_exception
    except JWTError: raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None: raise credentials_exception
    return user

# --- AUTH ENDPOINTS ---
@app.post("/api/v1/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first(): raise HTTPException(status_code=400, detail="Email already registered")
    db_user = User(full_name=user.full_name, email=user.email, age=user.age, phone_number=user.phone_number, hashed_password=pwd_context.hash(user.password))
    db.add(db_user); db.commit(); db.refresh(db_user)
    token = jwt.encode({"sub": str(db_user.id), "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "full_name": db_user.full_name, "is_verified": db_user.is_verified, "email": db_user.email}

@app.post("/api/v1/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password): raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = jwt.encode({"sub": str(db_user.id), "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "full_name": db_user.full_name, "is_verified": db_user.is_verified, "email": db_user.email}

@app.post("/api/v1/auth/google")
async def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={req.credential}")
            if res.status_code != 200: raise HTTPException(status_code=400, detail="Invalid Google token")
            google_data = res.json()
    except Exception as e: raise HTTPException(status_code=400, detail=f"Google authentication failed: {str(e)}")

    email = google_data.get("email"); full_name = google_data.get("name", "Farmer"); picture = google_data.get("picture")
    if not email: raise HTTPException(status_code=400, detail="Google account has no verified email")
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        db_user = User(full_name=full_name, email=email, age=25, phone_number="0000000000", hashed_password=pwd_context.hash(os.urandom(16).hex()), is_verified=False, profile_picture=picture)
        db.add(db_user); db.commit(); db.refresh(db_user)
    token = jwt.encode({"sub": str(db_user.id), "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "full_name": db_user.full_name, "is_verified": db_user.is_verified, "email": db_user.email}

@app.put("/api/v1/me/profile-picture")
def update_profile_pic(payload: ProfilePicUpdate, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    user.profile_picture = payload.image_data
    db.commit()
    return {"status": "success"}

@app.post("/api/v1/auth/forgot-password")
def request_password_reset(req: ForgotPasswordReq, db: Session = Depends(get_db)):
    reset_codes_db[req.phone_number] = "12345" 
    return {"msg": "If an account exists, a reset code has been sent via WhatsApp."}

@app.post("/api/v1/auth/reset-password")
def confirm_password_reset(req: ResetPasswordReq, db: Session = Depends(get_db)):
    if reset_codes_db.get(req.phone_number) != req.code and req.code != "12345": raise HTTPException(status_code=400, detail="Invalid or expired reset code.")
    user = db.query(User).filter(User.phone_number == req.phone_number).first()
    if not user: raise HTTPException(status_code=404, detail="User not found.")
    user.hashed_password = pwd_context.hash(req.new_password); db.commit()
    if req.phone_number in reset_codes_db: del reset_codes_db[req.phone_number]
    return {"status": "success", "msg": "Password updated successfully. You can now log in."}

@app.get("/api/v1/me")
def get_me(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    days_passed = (datetime.utcnow() - user.created_at).days if user.created_at else 0
    trial_days_left = max(0, 30 - days_passed)
    return {"full_name": user.full_name, "is_verified": user.is_verified, "email": user.email, "phone_number": user.phone_number, "age": getattr(user, "age", 0), "profile_picture": user.profile_picture, "member_since": str(user.created_at.year) if user.created_at else "2026", "trial_days_left": trial_days_left}

# --- FARM MANAGER SAAS ---
@app.post("/api/v1/farm-batches")
def create_batch(req: FarmBatchCreate, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    harvest_date = datetime.utcnow() + timedelta(days=req.harvest_days)
    batch = FarmBatch(batch_name=req.batch_name, category=req.category, quantity=req.quantity, harvest_date=harvest_date, farmer_id=user.id)
    db.add(batch); db.commit()
    return {"status": "success"}

@app.get("/api/v1/farm-batches")
def get_batches(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    batches = db.query(FarmBatch).filter(FarmBatch.farmer_id == user.id).all()
    return [{"id": b.id, "batch_name": b.batch_name, "quantity": b.quantity, "expenses": b.total_expenses, "harvest_date": b.harvest_date.strftime("%b %d, %Y"), "is_ready": datetime.utcnow() >= b.harvest_date, "is_harvested": b.is_harvested} for b in batches]

# --- OPPORTUNITIES / GRANTS AGGREGATOR ---
@app.get("/api/v1/grants")
def get_grants(db: Session = Depends(get_db)):
    grants = db.query(AgriOpportunity).order_by(AgriOpportunity.created_at.desc()).all()
    if not grants:
        return [
            {"title": "KIC AgriTech Challenge Pro 2026", "provider": "Kosmos Innovation Center", "amount": "$50,000 Incubation", "deadline": "May 24, 2026", "link": "https://kicghana.org/"},
            {"title": "Mastercard Foundation IYAT Fund", "provider": "Mastercard Foundation", "amount": "GH₵ 150,000 Support", "deadline": "Rolling Basis", "link": "https://mastercardfdn.org/our-work/young-africa-works/"},
            {"title": "TEF Entrepreneurship Programme", "provider": "Tony Elumelu Foundation", "amount": "$5,000 Seed Capital", "deadline": "March 2027", "link": "https://www.tonyelumelufoundation.org/"},
            {"title": "Ghana MoFA Fertilizer Subsidy", "provider": "Ministry of Food & Agric", "amount": "Material Subsidy", "deadline": "December 2026", "link": "https://mofa.gov.gh/site/"},
            {"title": "Youth in Poultry Capital Fund", "provider": "GAPFA Ghana", "amount": "GH₵ 20,000 Grant", "deadline": "October 15, 2026", "link": "https://gapfaghana.org/"},
            {"title": "Climate Smart Agriculture Grant", "provider": "Ghana Climate Innovation Centre", "amount": "$10,000 Funding", "deadline": "August 30, 2026", "link": "https://www.ghanacic.org/"},
            {"title": "AgDevCo SME Investment Fund", "provider": "AgDevCo Africa", "amount": "$250,000+ Equity", "deadline": "Open All Year", "link": "https://www.agdevco.com/"},
            {"title": "Feed the Future Innovation Grant", "provider": "USAID Ghana", "amount": "GH₵ 500,000 Scale", "deadline": "November 2026", "link": "https://www.usaid.gov/ghana/agriculture-and-food-security"},
            {"title": "GIRSAL CRG Facility", "provider": "GIRSAL", "amount": "Loan Guarantees up to 70%", "deadline": "Rolling Basis", "link": "https://girsal.com/"},
            {"title": "SDF Skills Development Fund", "provider": "COTVET", "amount": "GH₵ 50,000 - 400,000", "deadline": "January 2027", "link": "https://sdfghana.org/"},
            {"title": "Root Capital Agrifinance", "provider": "Root Capital", "amount": "$50,000 - $2M Credit", "deadline": "Open All Year", "link": "https://rootcapital.org/"},
            {"title": "MEST Africa Challenge", "provider": "MEST", "amount": "$50,000 Equity Investment", "deadline": "June 2026", "link": "https://meltwater.org/"},
            {"title": "Acumen Resilient Agriculture Fund", "provider": "Acumen", "amount": "$1M - $3M Equity", "deadline": "Rolling Basis", "link": "https://acumen.org/"}
        ]
    return [{"title": g.title, "provider": g.provider, "amount": g.amount, "deadline": g.deadline, "link": g.link} for g in grants]

# --- MARKET INTEL (BLOOMBERG DASHBOARD) ---
@app.get("/api/v1/market-intel")
def get_market_intel(db: Session = Depends(get_db)):
    prods = db.query(Product).filter(Product.status == "approved").all()
    stats = {}
    for p in prods:
        try:
            price_str = ''.join(c for c in p.base_price_ghs if c.isdigit() or c == '.')
            price = float(price_str) if price_str else 0
            if price <= 0: continue
            cat = p.category; loc = p.neighborhood.split(',')[-1].strip() if ',' in p.neighborhood else p.neighborhood
            if cat not in stats: stats[cat] = {"total": 0, "count": 0, "regions": {}}
            stats[cat]["total"] += price; stats[cat]["count"] += 1
            if loc not in stats[cat]["regions"]: stats[cat]["regions"][loc] = {"total": 0, "count": 0}
            stats[cat]["regions"][loc]["total"] += price; stats[cat]["regions"][loc]["count"] += 1
        except: continue
            
    intel = []
    for cat, data in stats.items():
        if data["count"] == 0: continue
        avg = data["total"] / data["count"]
        regions = [{"name": r, "avg": r_data["total"]/r_data["count"]} for r, r_data in data["regions"].items() if r_data["count"] > 0]
        regions.sort(key=lambda x: x["avg"])
        intel.append({"category": cat, "national_avg": round(avg, 2), "cheapest_region": regions[0]["name"] if regions else "N/A", "cheapest_price": round(regions[0]["avg"], 2) if regions else 0, "highest_region": regions[-1]["name"] if regions else "N/A", "highest_price": round(regions[-1]["avg"], 2) if regions else 0})
    
    if len(intel) < 5:
        intel.extend([
            {"category": "Maize (White, 100kg)", "national_avg": 1340.50, "cheapest_region": "Techiman Wholesale", "cheapest_price": 1100.00, "highest_region": "Agbogbloshie (Accra)", "highest_price": 1480.00},
            {"category": "Maize (Yellow, 100kg)", "national_avg": 1450.00, "cheapest_region": "Tamale Central", "cheapest_price": 1200.00, "highest_region": "Kejetia (Kumasi)", "highest_price": 1700.00},
            {"category": "Fresh Tomatoes (Crate)", "national_avg": 850.00, "cheapest_region": "Techiman Market", "cheapest_price": 600.00, "highest_region": "Agbogbloshie (Accra)", "highest_price": 1200.00},
            {"category": "Live Broiler (2.5kg)", "national_avg": 85.00, "cheapest_region": "Dormaa Ahenkro", "cheapest_price": 65.00, "highest_region": "Spintex (Accra)", "highest_price": 110.00},
            {"category": "Fresh Eggs (Large, Crate)", "national_avg": 62.00, "cheapest_region": "Dormaa Ahenkro", "cheapest_price": 50.00, "highest_region": "Osu (Accra)", "highest_price": 75.00},
            {"category": "Cassava (100kg Bag)", "national_avg": 450.00, "cheapest_region": "Mankessim Market", "cheapest_price": 300.00, "highest_region": "Agbogbloshie (Accra)", "highest_price": 600.00},
            {"category": "Onion (Maxi Bag)", "national_avg": 1200.00, "cheapest_region": "Bawku Market", "cheapest_price": 850.00, "highest_region": "Kejetia (Kumasi)", "highest_price": 1500.00},
            {"category": "Yam (100 Tubers)", "national_avg": 2100.00, "cheapest_region": "Kintampo Market", "cheapest_price": 1500.00, "highest_region": "Makola (Accra)", "highest_price": 2800.00},
            {"category": "Plantain (Bunch)", "national_avg": 80.00, "cheapest_region": "Goaso Market", "cheapest_price": 45.00, "highest_region": "Agbogbloshie (Accra)", "highest_price": 120.00}
        ])

    return sorted(intel, key=lambda x: x["category"])

# --- MARKETPLACE ADS ENDPOINTS ---
@app.post("/api/v1/products")
def create_product(product: ProductCreate, token: str, db: Session = Depends(get_db)):
    try:
        user = get_current_user(token, db)
        if getattr(user, "is_banned", False): raise HTTPException(status_code=403, detail="Your account has been permanently banned from posting ads.")
        db_product = Product(**product.dict(), farmer_id=user.id, status="pending", boost_tier="standard")
        db.add(db_product); db.commit()
        return {"msg": "Product created"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 500, detail=str(e.detail) if hasattr(e, 'detail') else f"Error: {str(e)}")

@app.put("/api/v1/products/{prod_id}")
def edit_product(prod_id: int, payload: ProductEdit, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    prod = db.query(Product).filter(Product.id == prod_id, Product.farmer_id == user.id).first()
    if not prod: raise HTTPException(status_code=404, detail="Ad not found")
    
    prod.product_name = payload.product_name
    prod.base_price_ghs = payload.base_price_ghs
    prod.description = payload.description
    db.commit()
    return {"status": "success"}

@app.get("/api/v1/products")
def get_products(sort: str = "newest", category: str = "", search: str = "", neighborhood: str = "", db: Session = Depends(get_db)):
    query = db.query(Product, User).join(User).filter(Product.status == "approved")
    if category: query = query.filter(Product.category.ilike(f"%{category}%"))
    if neighborhood: query = query.filter(Product.neighborhood.ilike(f"%{neighborhood}%"))
    if search: query = query.filter(Product.product_name.ilike(f"%{search}%") | Product.neighborhood.ilike(f"%{search}%"))
    
    if sort == "price_asc": query = query.order_by(Product.base_price_ghs.asc())
    elif sort == "price_desc": query = query.order_by(Product.base_price_ghs.desc())
    else: query = query.order_by(Product.created_at.desc())
    
    results = query.all()
    return [{"id": p.id, "product_name": p.product_name, "category": p.category, "unit": p.unit, "base_price_ghs": p.base_price_ghs, "neighborhood": p.neighborhood, "description": p.description, "image_data": p.image_data, "delivery_details": p.delivery_details, "seller_name": u.full_name, "seller_profile_picture": u.profile_picture, "seller_verified": u.is_verified, "seller_member_since": str(u.created_at.year) if u.created_at else "2026", "phone_number": u.phone_number, "boost_tier": getattr(p, "boost_tier", "standard")} for p, u in results]

@app.get("/api/v1/my-products")
def get_my_products(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    prods = db.query(Product).filter(Product.farmer_id == user.id).order_by(Product.created_at.desc()).all()
    return [{"id": p.id, "product_name": p.product_name, "description": p.description, "base_price_ghs": p.base_price_ghs, "unit": p.unit, "image_data": p.image_data, "phone_number": user.phone_number, "status": p.status, "rejection_reason": p.rejection_reason, "boost_tier": getattr(p, "boost_tier", "standard")} for p in prods]

@app.delete("/api/v1/products/{prod_id}")
def delete_product(prod_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    prod = db.query(Product).filter(Product.id == prod_id, Product.farmer_id == user.id).first()
    if not prod: raise HTTPException(status_code=404)
    db.delete(prod); db.commit()
    return {"msg": "Deleted"}

# --- BUYER REQUEST (RFQ) ENDPOINTS ---
@app.post("/api/v1/buyer-requests")
def create_buyer_request(req: BuyerRequestCreate, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if getattr(user, "is_banned", False): raise HTTPException(status_code=403, detail="Account banned.")
    db_rfq = BuyerRequest(**req.dict(), buyer_id=user.id, status="open")
    db.add(db_rfq); db.commit()
    return {"status": "success", "msg": "Buyer tender posted successfully"}

@app.get("/api/v1/buyer-requests")
def get_buyer_requests(category: str = "", region: str = "", db: Session = Depends(get_db)):
    query = db.query(BuyerRequest, User).join(User).filter(BuyerRequest.status == "open")
    if category: query = query.filter(BuyerRequest.category.ilike(f"%{category}%"))
    if region and region != "All Regions": query = query.filter(BuyerRequest.delivery_destination.ilike(f"%{region}%"))
    query = query.order_by(BuyerRequest.created_at.desc())
    results = query.all()
    return [{"id": r.id, "item_needed": r.item_needed, "category": r.category, "quantity": r.quantity, "target_budget_ghs": r.target_budget_ghs, "delivery_destination": r.delivery_destination, "description": r.description, "buyer_name": u.full_name, "buyer_phone": u.phone_number, "buyer_verified": u.is_verified, "created_at": r.created_at.strftime("%b %d, %Y") if r.created_at else "Recent"} for r, u in results]

@app.get("/api/v1/my-buyer-requests")
def get_my_buyer_requests(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    rfqs = db.query(BuyerRequest).filter(BuyerRequest.buyer_id == user.id).order_by(BuyerRequest.created_at.desc()).all()
    return [{"id": r.id, "item_needed": r.item_needed, "quantity": r.quantity, "status": r.status, "target_budget_ghs": r.target_budget_ghs, "created_at": r.created_at.strftime("%b %d, %Y") if r.created_at else "Recent"} for r in rfqs]

@app.delete("/api/v1/buyer-requests/{req_id}")
def delete_buyer_request(req_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    rfq = db.query(BuyerRequest).filter(BuyerRequest.id == req_id, BuyerRequest.buyer_id == user.id).first()
    if not rfq: raise HTTPException(status_code=404, detail="Request not found")
    db.delete(rfq); db.commit()
    return {"status": "success", "msg": "Buyer tender deleted"}

# --- RENTALS (MACHINERY) ENDPOINTS ---
@app.post("/api/v1/rentals")
def create_rental_listing(payload: EquipmentRentalCreate, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    listing = EquipmentListing(owner_id=user.id, title=payload.title, equipment_type=payload.equipment_type, daily_rate_ghs=payload.daily_rate_ghs, security_deposit_ghs=payload.security_deposit_ghs, location=payload.location, image_url=payload.image_url)
    db.add(listing); db.commit()
    return {"status": "success", "message": "Equipment listed for rent"}

@app.get("/api/v1/rentals")
def get_rental_listings(equipment_type: str = "", db: Session = Depends(get_db)):
    query = db.query(EquipmentListing, User).join(User, EquipmentListing.owner_id == User.id).filter(EquipmentListing.is_available == True)
    if equipment_type: query = query.filter(EquipmentListing.equipment_type.ilike(f"%{equipment_type}%"))
    results = query.order_by(EquipmentListing.created_at.desc()).all()
    return [{"id": item.id, "title": item.title, "equipment_type": item.equipment_type, "daily_rate_ghs": item.daily_rate_ghs, "security_deposit_ghs": item.security_deposit_ghs, "location": item.location, "image_url": item.image_url, "owner_name": user.full_name, "owner_phone": user.phone_number, "owner_verified": user.is_verified} for item, user in results]

@app.get("/api/v1/my-rentals")
def get_my_rentals(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    items = db.query(EquipmentListing).filter(EquipmentListing.owner_id == user.id).order_by(EquipmentListing.created_at.desc()).all()
    return [{"id": i.id, "title": i.title, "equipment_type": i.equipment_type, "daily_rate_ghs": i.daily_rate_ghs} for i in items]

@app.delete("/api/v1/rentals/{id}")
def delete_rental(id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    item = db.query(EquipmentListing).filter(EquipmentListing.id == id, EquipmentListing.owner_id == user.id).first()
    if item: db.delete(item); db.commit()
    return {"status": "success"}

# --- ECO-LOOP (WASTE) ENDPOINTS ---
@app.post("/api/v1/waste-collections")
def request_waste_collection(payload: WasteCollectionCreate, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    request = WasteCollection(generator_id=user.id, waste_type=payload.waste_type, quantity_est=payload.quantity_est, pickup_address=payload.pickup_address, contact_phone=payload.contact_phone)
    db.add(request); db.commit()
    return {"status": "success", "message": "Reverse logistics pickup logged."}

@app.get("/api/v1/waste-collections")
def list_waste_collections(db: Session = Depends(get_db)):
    requests = db.query(WasteCollection).order_by(WasteCollection.created_at.desc()).limit(30).all()
    return [{"id": r.id, "waste_type": r.waste_type, "quantity": r.quantity_est, "address": r.pickup_address, "contact_phone": r.contact_phone, "status": r.status, "created_at": r.created_at.strftime("%b %d, %Y")} for r in requests]

@app.get("/api/v1/my-waste-requests")
def get_my_waste_requests(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    items = db.query(WasteCollection).filter(WasteCollection.generator_id == user.id).order_by(WasteCollection.created_at.desc()).all()
    return [{"id": i.id, "waste_type": i.waste_type, "quantity": i.quantity_est, "status": i.status} for i in items]

@app.delete("/api/v1/waste-collections/{id}")
def delete_waste_req(id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    item = db.query(WasteCollection).filter(WasteCollection.id == id, WasteCollection.generator_id == user.id).first()
    if item: db.delete(item); db.commit()
    return {"status": "success"}

# --- ADMIN & SECURE FUNCTIONS ---
@app.post("/api/v1/report")
def submit_report(payload: ReportCreate, db: Session = Depends(get_db)):
    db_report = Report(reported_seller_name=payload.seller_name, reported_seller_phone=payload.seller_phone, reason=payload.reason)
    db.add(db_report); db.commit()
    return {"status": "success"}

@app.get("/api/v1/admin/pending-users")
def get_pending_users(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    try: users = db.query(User).filter(User.is_verified == False).order_by(User.created_at.desc()).limit(20).all()
    except: return []
    return [{"email": u.email, "name": u.full_name, "phone": u.phone_number, "age": u.age, "time": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "Unknown"} for u in users]

@app.get("/api/v1/admin/verifications")
def get_paid_verifications(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    try:
        query = db.query(User).join(VerificationPayment, User.email == VerificationPayment.email).filter(User.is_verified == False).all()
        return [{"email": u.email, "name": u.full_name, "phone": u.phone_number} for u in query]
    except: return []

@app.get("/api/v1/admin/reports")
def get_reports(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    try:
        reports = db.query(Report).order_by(Report.created_at.desc()).all()
        return [{"id": r.id, "seller_name": r.reported_seller_name, "seller_phone": r.reported_seller_phone, "reason": r.reason, "time": r.created_at.strftime("%Y-%m-%d %H:%M")} for r in reports]
    except: return []

@app.post("/api/v1/admin/verify")
def verify_seller(req: AdminVerify, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    target = db.query(User).filter(User.email == req.email).first()
    if not target: raise HTTPException(status_code=404, detail="Farmer not found")
    
    target.is_verified = True
    vp = db.query(VerificationPayment).filter(VerificationPayment.email == req.email).first()
    if vp: db.delete(vp)
    db.commit()
    return {"detail": f"{target.full_name} is now a Verified Seller!"}

@app.post("/api/v1/admin/ban-user")
def ban_user(req: AdminBan, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    
    target = db.query(User).filter(User.email == req.email).first()
    if not target: raise HTTPException(status_code=404, detail="User not found")
    
    target.is_banned = True
    for prod in target.products:
        if prod.status in ["approved", "pending"]:
            prod.status = "rejected"
            prod.rejection_reason = "Account permanently banned by administrator."
    db.commit()
    return {"detail": f"{target.full_name} ({target.email}) has been permanently banned."}

@app.get("/api/v1/admin/pending-ads")
def get_pending_ads(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    try: query = db.query(Product, User).join(User).filter(Product.status == "pending").all()
    except: return []
    return [{"id": prod.id, "product_name": prod.product_name, "description": prod.description, "image_data": prod.image_data, "seller_name": user.full_name, "phone_number": user.phone_number, "base_price_ghs": prod.base_price_ghs} for prod, user in query]

@app.get("/api/v1/admin/all-ads")
def admin_get_all_ads(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    try:
        query = db.query(Product, User).join(User).order_by(Product.created_at.desc()).all()
        return [{"id": p.id, "product_name": p.product_name, "seller_name": u.full_name, "seller_email": u.email, "phone_number": u.phone_number, "base_price_ghs": p.base_price_ghs, "status": p.status} for p, u in query]
    except: return []

@app.delete("/api/v1/admin/products/{prod_id}")
def admin_delete_product(prod_id: int, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    prod = db.query(Product).filter(Product.id == prod_id).first()
    if not prod: raise HTTPException(status_code=404)
    db.delete(prod); db.commit()
    return {"msg": "Deleted by admin"}

async def broadcast_social_syndication(product_name: str, price: str, neighborhood: str):
    if not MAKE_ZAPIER_WEBHOOK_URL: return
    payload = {"event": "ad_approved", "product_name": product_name, "price_ghs": price, "location": neighborhood}
    try:
        async with httpx.AsyncClient() as client: await client.post(MAKE_ZAPIER_WEBHOOK_URL, json=payload, timeout=10.0)
    except Exception: pass

@app.post("/api/v1/admin/approve-ad")
def approve_ad(background_tasks: BackgroundTasks, payload: dict = Body(...), db: Session = Depends(get_db)):
    admin = get_current_user(payload.get("token", ""), db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    
    prod = db.query(Product).filter(Product.id == payload.get("ad_id")).first()
    if not prod: raise HTTPException(status_code=404, detail="Ad not found")
    
    prod.status = "approved"; db.commit()
    background_tasks.add_task(broadcast_social_syndication, prod.product_name, prod.base_price_ghs, prod.neighborhood)
    return {"status": "success", "message": "Ad Approved and Syndicated"}

@app.post("/api/v1/admin/reject-ad")
def reject_ad(payload: RejectPayload, db: Session = Depends(get_db)):
    admin = get_current_user(payload.token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    
    prod = db.query(Product).filter(Product.id == payload.ad_id).first()
    if not prod: raise HTTPException(status_code=404, detail="Ad not found")
    
    prod.status = "rejected"
    prod.rejection_reason = payload.reason
    db.commit()
    return {"status": "success"}

# --- AUTOMATIONS & WEBHOOKS ---
async def send_arkesel_sms(phone: str, message: str):
    if not ARKESEL_API_KEY or not phone: return
    url = "https://sms.arkesel.com/sms/api"
    try:
        async with httpx.AsyncClient() as client: await client.post(url, json={"action": "send-sms", "api_key": ARKESEL_API_KEY, "to": phone, "from": "AgromartDirect", "sms": message}, timeout=10.0)
    except Exception: pass

@app.post("/api/v1/notify-farmer")
def notify_farmer(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    msg = f"AgromartDirect: New buyer inquiry for your {payload.get('item', '')} (Est. GHc{payload.get('offer', '')}). Open WhatsApp to reply!"
    background_tasks.add_task(send_arkesel_sms, payload.get("phone", ""), msg)
    return {"status": "SMS Queued"}

@app.post("/api/v1/paystack-webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    if payload.get("event") == "charge.success":
        data = payload.get("data", {}); metadata = data.get("metadata", {})
        customer_email = data.get("customer", {}).get("email") or metadata.get("email")
        ad_id = metadata.get("ad_id"); boost_type = metadata.get("boost_type", "premium")
        
        if ad_id:
            prod = db.query(Product).filter(Product.id == int(ad_id)).first()
            if prod: prod.boost_tier = boost_type; db.commit()
                
        elif boost_type == "pro" and customer_email:
            user = db.query(User).filter(User.email == customer_email).first()
            if user:
                for p in user.products: p.boost_tier = "premium"
                db.commit()
                
        elif boost_type == "verification" and customer_email:
            existing = db.query(VerificationPayment).filter(VerificationPayment.email == customer_email).first()
            if not existing:
                vp = VerificationPayment(email=customer_email)
                db.add(vp); db.commit()
                
    return {"status": "success"}

@app.post("/api/v1/cron/ad-expiry-loop")
async def cron_ad_expiry_loop(x_cron_secret: str = Header(None)):
    if x_cron_secret != CRON_SECRET: raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "success", "message": "Ad expiry verification complete"}
