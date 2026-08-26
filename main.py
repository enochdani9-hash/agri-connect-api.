import os
import bcrypt
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from jose import jwt, JWTError

# ==============================================================================
# 1. SECURITY & CONFIGURATION
# ==============================================================================
SECRET_KEY = "super-secret-agriconnect-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ==============================================================================
# 2. CLOUD DATABASE (Supabase)
# ==============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agriconnect_jiji.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users_v2"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# V3 Table to support images without breaking your old database
class ProductDB(Base):
    __tablename__ = "products_v3"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_name = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    base_price_ghs = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    seller_name = Column(String, nullable=False)
    seller_id = Column(Integer, nullable=False)
    phone_number = Column(String, nullable=False)
    neighborhood = Column(String, index=True, nullable=False)
    image_data = Column(Text, nullable=True) # NEW: Stores the compressed image string
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
    full_name: str
    email: str
    phone_number: str
    age: int
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    full_name: str

class ProductCreate(BaseModel):
    product_name: str
    category: str
    base_price_ghs: float
    unit: str
    neighborhood: str
    image_data: Optional[str] = None # NEW

class ProductResponse(BaseModel):
    id: int
    product_name: str
    category: str
    base_price_ghs: float
    unit: str
    seller_name: str
    phone_number: str
    neighborhood: str
    image_data: Optional[str] = None # NEW
    created_at: datetime

# ==============================================================================
# 4. FASTAPI APP & ENDPOINTS
# ==============================================================================
app = FastAPI(title="AgriConnect Classifieds API", version="4.1.0")

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
        return db.query(UserDB).filter(UserDB.email == email).first()
    except JWTError:
        return None

@app.post("/api/v1/signup", response_model=Token)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = UserDB(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        age=user_data.age
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"access_token": create_access_token(data={"sub": new_user.email}), "token_type": "bearer", "full_name": new_user.full_name}

@app.post("/api/v1/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(data={"sub": user.email}), "token_type": "bearer", "full_name": user.full_name}

@app.get("/api/v1/me")
def verify_token(token: str = Query(...), db: Session = Depends(get_db)):
    user = get_current_user_from_token(token, db)
    if not user: raise HTTPException(status_code=401, detail="Invalid token")
    return {"full_name": user.full_name, "email": user.email, "phone_number": user.phone_number}

@app.post("/api/v1/products", response_model=ProductResponse)
def create_product(product: ProductCreate, token: str = Query(...), db: Session = Depends(get_db)):
    user = get_current_user_from_token(token, db)
    if not user: raise HTTPException(status_code=401, detail="Must be logged in")

    db_product = ProductDB(
        **product.model_dump(),
        seller_name=user.full_name,
        seller_id=user.id,
        phone_number=user.phone_number,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return ProductResponse(**db_product.__dict__)

@app.get("/api/v1/products", response_model=List[ProductResponse])
def list_products(category: Optional[str] = Query(None), neighborhood: Optional[str] = Query(None), search: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(ProductDB)
    if category: query = query.filter(ProductDB.category.ilike(f"%{category}%"))
    if neighborhood: query = query.filter(ProductDB.neighborhood.ilike(f"%{neighborhood}%"))
    if search: query = query.filter((ProductDB.product_name.ilike(f"%{search}%")) | (ProductDB.neighborhood.ilike(f"%{search}%")))
    
    products = query.order_by(ProductDB.created_at.desc()).all()
    return [ProductResponse(**p.__dict__) for p in products]
