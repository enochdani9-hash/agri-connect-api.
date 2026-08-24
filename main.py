import random
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
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# For Authentication (passlib for passwords, jose for JWT tokens)
from passlib.context import CryptContext
from jose import jwt, JWTError

# ==============================================================================
# 1. SECURITY & CONFIGURATION
# ==============================================================================
SECRET_KEY = "super-secret-agriconnect-key"  # In production, use environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

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

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

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
# 4. FASTAPI APP & AUTH DEPENDENCIES
# ==============================================================================
app = FastAPI(title="AgriConnect Global API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(UserDB).filter(UserDB.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# ==============================================================================
# 5. AUTHENTICATION ENDPOINTS (Restored!)
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
    return {"access_token": access_token, "token_type": "bearer", "role": new_user.role}

@app.post("/api/v1/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

# ==============================================================================
# 6. MARKETPLACE & LOGISTICS (The Upgrades)
# ==============================================================================
EXCHANGE_RATES_TO_GHS = {"GHS": 1.0, "USD": 0.065, "EUR": 0.060, "NGN": 98.50}

@app.post("/api/v1/products", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)):
    if current_user.role != "farmer":
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

# Logistics OTP Mock DB
shipments_db = {}

@app.post("/api/v1/logistics/dispatch/{order_id}")
def initiate_dispatch(order_id: int):
    otp = str(random.randint(100000, 999999))
    shipments_db[order_id] = {"otp": otp, "status": "DISPATCHED"}
    return {"message": "Dispatch initiated", "buyer_otp": otp}

# WebSockets
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
