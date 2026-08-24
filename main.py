import random
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from jose import jwt, JWTError

# ==============================================================================
# 1. SECURITY & CONFIGURATION
# ==============================================================================
SECRET_KEY = "super-secret-agriconnect-key"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Generates a secure hash using standard bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ==============================================================================
# 2. DATABASE SETUP
# ==============================================================================
DATABASE_URL = "sqlite:///./agriconnect.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False) # 'farmer' or 'buyer'
    full_name = Column(String, nullable=False)
    location_or_region = Column(String, nullable=False)

class ProductDB(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_name = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)  
    base_price_ghs = Column(Float, nullable=False)
    quantity_available = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)                 
    farmer_name = Column(String, nullable=False)
    farmer_id = Column(Integer, nullable=False)
    location = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class OrderDB(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, nullable=False)
    buyer_id = Column(Integer, nullable=False)
    buyer_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount_ghs = Column(Float, nullable=False)
    target_currency = Column(String, default="GHS")
    converted_total = Column(Float, nullable=False)
    status = Column(String, default="PENDING_ESCROW")  
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================================================================
# 3. PYDANTIC SCHEMAS
# ==============================================================================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = Field(..., description="'farmer' or 'buyer'")
    full_name: str
    location_or_region: str

class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str

class ProductCreate(BaseModel):
    product_name: str
    category: str 
    base_price_ghs: float 
    quantity_available: int 
    unit: str
    location: str 
    description: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    product_name: str
    category: str
    base_price_ghs: float
    converted_price: float
    currency: str
    quantity_available: int
    unit: str
    farmer_name: str
    location: str
    description: Optional[str]

class OrderCreate(BaseModel):
    product_id: int
    quantity: int
    currency: str = "GHS"

# ==============================================================================
# 4. FASTAPI APP & AUTH MIDDLEWARE
# ==============================================================================
app = FastAPI(title="AgriConnect Global API", version="2.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_current_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return db.query(UserDB).filter(UserDB.email == email).first()
    except JWTError:
        return None

# ==============================================================================
# 5. AUTHENTICATION ENDPOINTS
# ==============================================================================
@app.post("/api/v1/signup", response_model=Token)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user_data.password)
    new_user = UserDB(
        email=user_data.email,
        hashed_password=hashed_pw,
        role=user_data.role,
        full_name=user_data.full_name,
        location_or_region=user_data.location_or_region
    )
    db.add(new_user)
    db.commit()
    
    access_token = create_access_token(data={"sub": new_user.email, "role": new_user.role})
    return {"access_token": access_token, "token_type": "bearer", "role": new_user.role, "full_name": new_user.full_name}

@app.post("/api/v1/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "full_name": user.full_name}

# ==============================================================================
# 6. MARKETPLACE (Products & Orders)
# ==============================================================================
EXCHANGE_RATES_TO_GHS = {"GHS": 1.0, "USD": 0.065, "EUR": 0.060, "NGN": 98.50}

@app.post("/api/v1/products", response_model=ProductResponse)
def create_product(product: ProductCreate, token: str, db: Session = Depends(get_db)):
    current_user = get_current_user_from_token(token, db)
    if not current_user or current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can post products")
        
    db_product = ProductDB(
        **product.model_dump(), 
        farmer_name=current_user.full_name,
        farmer_id=current_user.id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return ProductResponse(**db_product.__dict__, converted_price=db_product.base_price_ghs, currency="GHS")

@app.get("/api/v1/products", response_model=List[ProductResponse])
def list_products(currency: str = "GHS", db: Session = Depends(get_db)):
    products = db.query(ProductDB).all()
    rate = EXCHANGE_RATES_TO_GHS.get(currency.upper(), 1.0)
    
    return [
        ProductResponse(
            **p.__dict__, 
            converted_price=round(p.base_price_ghs * rate, 2), 
            currency=currency.upper()
        ) for p in products
    ]

# ==============================================================================
# 7. LOGISTICS & DISPATCH (OTP Verification)
# ==============================================================================
shipments_db = {}

@app.post("/api/v1/logistics/dispatch/{order_id}")
def initiate_dispatch(order_id: int):
    otp = str(random.randint(100000, 999999))
    shipments_db[order_id] = {"otp": otp, "status": "DISPATCHED"}
    return {"message": "Dispatch initiated successfully", "buyer_otp": otp}

# ==============================================================================
# 8. LIVE CHAT (WebSockets)
# ==============================================================================
chat_manager = {}

@app.websocket("/ws/chat/{order_id}/{user_name}")
async def websocket_chat(websocket: WebSocket, order_id: int, user_name: str):
    await websocket.accept()
    if order_id not in chat_manager:
        chat_manager[order_id] = []
    chat_manager[order_id].append(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            for connection in chat_manager[order_id]:
                await connection.send_json({"sender": user_name, "message": text})
    except WebSocketDisconnect:
        chat_manager[order_id].remove(websocket)

# ==============================================================================
# 9. SMART PRICING & MARKET INTELLIGENCE
# ==============================================================================
REGIONAL_BENCHMARKS = {
    "poultry": {"avg_price": 120.0, "unit": "birds", "min": 95.0, "max": 140.0},
    "tomatoes": {"avg_price": 450.0, "unit": "crates", "min": 380.0, "max": 520.0},
}

@app.get("/api/v1/intelligence/price-advisory")
def get_price_advisory(commodity: str, farmer_price: float, quantity: int = 1):
    key = commodity.lower().strip()
    benchmark = REGIONAL_BENCHMARKS.get(key)

    if not benchmark:
        return {"status": "NO_HISTORICAL_DATA", "message": "No regional data available."}

    avg = benchmark["avg_price"]
    diff_percent = round(((farmer_price - avg) / avg) * 100, 1)

    return {
        "commodity": commodity,
        "farmer_price": farmer_price,
        "regional_average": avg,
        "price_variance": f"{diff_percent}%",
        "benchmark_range": f"{benchmark['min']} - {benchmark['max']} GHS per {benchmark['unit']}",
    }
