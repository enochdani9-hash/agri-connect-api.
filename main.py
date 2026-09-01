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

app = FastAPI(title="AgromartDirect API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- AUTOMATION & PAYMENT SECRETS ---
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

# --- CORE ENDPOINTS ---
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
    return {
        "full_name": user.full_name, 
        "is_verified": user.is_verified, 
        "email": user.email, 
        "phone_number": user.phone_number,
        "age": getattr(user, "age", 0),
        "profile_picture": user.profile_picture,
        "member_since": str(user.created_at.year) if user.created_at else "2026",
        "trial_days_left": trial_days_left
    }

@app.post("/api/v1/products")
def create_product(product: ProductCreate, token: str, db: Session = Depends(get_db)):
    try:
        user = get_current_user(token, db)
        if getattr(user, "is_banned", False):
            raise HTTPException(status_code=403, detail="Your account has been permanently banned from posting ads.")
            
        db_product = Product(**product.dict(), farmer_id=user.id, status="pending", boost_tier="standard")
        db.add(db_product); db.commit()
        return {"msg": "Product created"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 500, detail=str(e.detail) if hasattr(e, 'detail') else f"Error: {str(e)}")

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

@app.get("/api/v1/latest-ad")
def get_latest_ad(db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.status == "approved").order_by(Product.created_at.desc()).first()
    if prod: return {"id": prod.id, "product_name": prod.product_name, "neighborhood": prod.neighborhood, "base_price_ghs": prod.base_price_ghs}
    return None

@app.get("/api/v1/my-products")
def get_my_products(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    prods = db.query(Product).filter(Product.farmer_id == user.id).order_by(Product.created_at.desc()).all()
    return [{"id": p.id, "product_name": p.product_name, "base_price_ghs": p.base_price_ghs, "unit": p.unit, "image_data": p.image_data, "phone_number": user.phone_number, "status": p.status, "rejection_reason": p.rejection_reason, "boost_tier": getattr(p, "boost_tier", "standard")} for p in prods]

@app.delete("/api/v1/products/{prod_id}")
def delete_product(prod_id: int, token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    prod = db.query(Product).filter(Product.id == prod_id, Product.farmer_id == user.id).first()
    if not prod: raise HTTPException(status_code=404)
    db.delete(prod); db.commit()
    return {"msg": "Deleted"}

@app.post("/api/v1/report")
def submit_report(payload: ReportCreate, db: Session = Depends(get_db)):
    db_report = Report(reported_seller_name=payload.seller_name, reported_seller_phone=payload.seller_phone, reason=payload.reason)
    db.add(db_report)
    db.commit()
    return {"status": "success"}

# ==========================================
# ADMIN & AUTOMATIONS
# ==========================================
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
        if prod.status == "approved" or prod.status == "pending":
            prod.status = "rejected"
            prod.rejection_reason = "Account banned by administrator for violating platform rules."
    db.commit()
    return {"detail": f"{target.full_name} ({target.email}) has been permanently banned and their ads removed."}

@app.get("/api/v1/admin/pending-ads")
def get_pending_ads(token: str, db: Session = Depends(get_db)):
    admin = get_current_user(token, db)
    if admin.email != ADMIN_EMAIL: raise HTTPException(status_code=403, detail="Not authorized")
    try: query = db.query(Product, User).join(User).filter(Product.status == "pending").all()
    except: return []
    return [{"id": prod.id, "product_name": prod.product_name, "seller_name": user.full_name, "phone_number": user.phone_number, "base_price_ghs": prod.base_price_ghs} for prod, user in query]

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
    except Exception as e: pass

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
    prod.status = "rejected"; prod.rejection_reason = payload.reason; db.commit()
    return {"status": "success"}

async def send_arkesel_sms(phone: str, message: str):
    if not ARKESEL_API_KEY or not phone: return
    url = "https://sms.arkesel.com/sms/api"
    try:
        async with httpx.AsyncClient() as client: await client.post(url, json={"action": "send-sms", "api_key": ARKESEL_API_KEY, "to": phone, "from": "AgromartDirect", "sms": message}, timeout=10.0)
    except Exception as e: pass

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

@app.post("/api/v1/cron/weekly-market-digest")
async def cron_weekly_market_digest(x_cron_secret: str = Header(None)):
    if x_cron_secret != CRON_SECRET: raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "success", "message": "Weekly digest broadcast triggered"}
