import os
from datetime import datetime, timedelta
from typing import List, Optional
import httpx
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Header, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text, DateTime
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

app = FastAPI(title="AgriConnect API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- AUTOMATION SECRETS ---
ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY", "")
MAKE_ZAPIER_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
CRON_SECRET = os.getenv("CRON_SECRET", "super-secret-cron-key-123")
ADMIN_EMAIL = "enochdani9@gmail.com"

# --- DATABASE MODELS ---
class User(Base):
    __tablename__ = "users_v3"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    age = Column(Integer)
    phone_number = Column(String)
    hashed_password = Column(String)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    products = relationship("Product", back_populates="owner")

class Product(Base):
    __tablename__ = "products_v5"  
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, index=True)
    category = Column(String, index=True)
    unit = Column(String)
    base_price_ghs = Column(String)  
    neighborhood = Column(String)
    description = Column(String, nullable=True)
    image_data = Column(Text, nullable=True)
    farmer_id = Column(Integer, ForeignKey("users_v3.id"))
    status = Column(String, default="pending")       
    rejection_reason = Column(String, nullable=True) 
    boost_tier = Column(String, default="standard")  
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="products")

Base.metadata.create_all(bind=engine)

# --- SCHEMAS ---
class UserCreate(BaseModel):
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
    description: Optional[str] = None
    image_data: Optional[str] = None

class AdminVerify(BaseModel):
    email: str

class RejectPayload(BaseModel):
    token: str
    ad_id: int
    reason: str

# --- DEPENDENCIES ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

# --- CORE ENDPOINTS ---
@app.post("/api/v1/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = pwd_context.hash(user.password)
    db_user = User(full_name=user.full_name, email=user.email, age=user.age, phone_number=user.phone_number, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    token = jwt.encode({"sub": str(db_user.id), "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "full_name": db_user.full_name, "is_verified": db_user.is_verified, "email": db_user.email}

@app.post("/api/v1/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = jwt.encode({"sub": str(db_user.id), "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "full_name": db_user.full_name, "is_verified": db_user.is_verified, "email": db_user.email}

@app.get("/api/v1/me")
def get_me(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    days_since_creation = (datetime.utcnow() - user.created_at).days if user.created_at else 0
    trial_days_left = max(0, 30 - days_since_creation)
    return {
        "full_name": user.full_name, 
        "is_verified": user.is_verified, 
        "email": user.email,
        "phone_number": user.phone_number,
        "trial_days_left": trial_days_left
    }

@app.post("/api/v1/products")
def create_product(product: ProductCreate, token: str, db: Session = Depends(get_db)):
    try:
        user = get_current_user(token, db)
        db_product = Product(
            product_name=product.product_name,
            category=product.category,
            unit=product.unit,
            base_price_ghs=product.base_price_ghs,
            neighborhood=product.neighborhood,
            description=product.description,
            image_data=product.image_data,
            farmer_id=user.id,
            status="pending",
            boost_tier="standard"
        )
        db.add(db_product)
        db.commit()
        return {"msg": "Product created"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database sync failed. Error: {str(e)}")

@app.get("/api/v1/products")
def get_products(sort: str = "newest", category: str = "", search: str = "", neighborhood: str = "", db: Session = Depends(get_db)):
    query = db.query(Product, User).join(User).filter(Product.status == "approved")
    
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if neighborhood:
        query = query.filter(Product.neighborhood.ilike(f"%{neighborhood}%"))
    if search:
        query = query.filter(Product.product_name.ilike(f"%{search}%") | Product.neighborhood.ilike(f"%{search}%"))

    if sort == "price_asc":
        query = query.order_by(Product.base_price_ghs.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.base_price_ghs.desc())
    else:
        query = query.order_by(Product.created_at.desc())
        
    results = query.all()
    
    out = []
    for prod, user in results:
        out.append({
            "id": prod.id,
            "product_name": prod.product_name,
            "category": prod.category,
            "unit": prod.unit,
            "base_price_ghs": prod.base_price_ghs,
            "neighborhood": prod.neighborhood,
            "description": prod.description,
            "image_data": prod.image_data,
            "seller_name": user.full_name,
            "seller_verified": user.is_verified,
            "seller_member_since": str(user.created_at.year) if user.created_at else "2026",
            "phone_number": user.phone_number,
            "boost_tier": getattr(prod, "boost_tier", "standard")
        })
    return out

@app.get("/api/v1/my-products")
def get_my_products(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    prods = db.query(Product).filter(Product.farmer_id == user.id).order_by(Product.created_at.desc()).all()
    
    out = []
    for p in prods:
        out.append({
            "id": p.id,
            "product_name": p.product_name,
            "base_price_ghs": p.base_price_ghs,
            "unit": p.unit,
            "image_data": p.image_data,
            "phone_number": user.phone_number,
            "status": p.status,
            "rejection_reason": p.rejection_reason
        })
    return out

@app.delete("/api/v1/products/{prod_id}")
def delete_product(prod_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    prod = db.query(Product).filter(Product.id == prod_id, Product.farmer_id == user.id).first()
    if not prod: raise HTTPException(status_code=404)
    db.delete(prod)
    db.commit()
    return {"msg": "Deleted"}

@app.get("/api/v1/locations")
def get_locations(db: Session = Depends(get_db)):
    locs = db.query(Product.neighborhood).distinct().all()
    return [l[0] for l in locs if l[0]]

# ==========================================
# ADMIN & AUTOMATIONS
# ==========================================
@app.post("/api/v1/admin/verify")
def verify_seller(req: AdminVerify, token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Not authorized")
    target = db.query(User).filter(User.email == req.email).first()
    if not target: raise HTTPException(status_code=404, detail="Farmer not found")
    target.is_verified = True
    db.commit()
    return {"detail": f"{target.full_name} is now a Verified Seller!"}

@app.get("/api/v1/admin/pending-ads")
def get_pending_ads(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        query = db.query(Product, User).join(User).filter(Product.status == "pending").all()
    except:
        return []
        
    out = []
    for prod, user in query:
        out.append({
            "id": prod.id,
            "product_name": prod.product_name,
            "seller_name": user.full_name,
            "phone_number": user.phone_number,
            "base_price_ghs": prod.base_price_ghs
        })
    return out

async def broadcast_social_syndication(product_name: str, price: str, neighborhood: str):
    if not MAKE_ZAPIER_WEBHOOK_URL: return
    payload = {"event": "ad_approved", "product_name": product_name, "price_ghs": price, "location": neighborhood}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(MAKE_ZAPIER_WEBHOOK_URL, json=payload, timeout=10.0)
    except Exception as e: print(f"Syndication Webhook dispatch failed: {e}")

@app.post("/api/v1/admin/approve-ad")
def approve_ad(background_tasks: BackgroundTasks, payload: dict = Body(...), db: Session = Depends(get_db)):
    token = payload.get("token", "")
    ad_id = payload.get("ad_id")
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    
    prod = db.query(Product).filter(Product.id == ad_id).first()
    if not prod: raise HTTPException(status_code=404, detail="Ad not found")
    
    prod.status = "approved"
    db.commit()
    
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

async def send_arkesel_sms(phone: str, message: str):
    if not ARKESEL_API_KEY or not phone: return
    url = "https://sms.arkesel.com/sms/api"
    payload = {"action": "send-sms", "api_key": ARKESEL_API_KEY, "to": phone, "from": "AgriConnect", "sms": message}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
    except Exception as e: print(f"SMS Gateway dispatch failed: {e}")

@app.post("/api/v1/notify-farmer")
def notify_farmer(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    phone = payload.get("phone", "")
    item = payload.get("item", "")
    offer = payload.get("offer", "")
    msg = f"AgriConnect: New buyer inquiry for your {item} (Est. GHc{offer}). Open WhatsApp to reply!"
    
    background_tasks.add_task(send_arkesel_sms, phone, msg)
    return {"status": "SMS Queued"}

# Checkout Mock Endpoint for Pricing Tiers
@app.post("/api/v1/checkout/init")
def init_checkout(payload: dict = Body(...), db: Session = Depends(get_db)):
    # Mocking a payment gateway integration (Paystack MoMo)
    return {"status": "success", "message": "Payment gateway integration pending."}

@app.post("/api/v1/paystack-webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    if payload.get("event") == "charge.success":
        metadata = payload.get("data", {}).get("metadata", {})
        ad_id = metadata.get("ad_id")
        boost_type = metadata.get("boost_type", "featured")
        if ad_id:
            prod = db.query(Product).filter(Product.id == ad_id).first()
            if prod:
                prod.boost_tier = boost_type
                db.commit()
    return {"status": "success"}

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
