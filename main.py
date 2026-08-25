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
from pydantic import BaseModel, Field
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
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    """Generates a secure hash using standard bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ==============================================================================
# 2. DATABASE CONFIGURATION (SQLite)
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
    role = Column(String, nullable=False, default="buyer")  # 'farmer' or 'buyer'
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
    farmer_id = Column(Integer, nullable=True)
    location = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class OrderDB(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, nullable=False)
    buyer_id = Column(Integer, nullable=True)
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
    email: str
    password: str
    role: Optional[str] = "buyer"
    full_name: Optional[str] = None
    name: Optional[str] = None
    location_or_region: Optional[str] = "Accra"
    location: Optional[str] = None

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
    buyer_name: Optional[str] = "Anonymous Buyer"
    quantity: int
    currency: str = "GHS"

class OrderResponse(BaseModel):
    id: int
    product_id: int
    buyer_name: str
    quantity: int
    total_amount_ghs: float
    target_currency: str
    converted_total: float
    status: str
    created_at: datetime

class DispatchUpdate(BaseModel):
    status: str
    current_location: str
    driver_notes: Optional[str] = None

class DeliveryVerification(BaseModel):
    order_id: int
    delivery_otp: str

# ==============================================================================
# 4. FASTAPI APP & CORS
# ==============================================================================
app = FastAPI(title="AgriConnect Global API", version="2.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXCHANGE_RATES_TO_GHS = {
    "GHS": 1.0,
    "USD": 0.065,
    "EUR": 0.060,
    "GBP": 0.052,
    "NGN": 98.50,
    "XOF": 40.00,
}

REGIONAL_BENCHMARKS = {
    "poultry": {"avg_price": 120.0, "unit": "birds", "min": 95.0, "max": 140.0},
    "tomatoes": {"avg_price": 450.0, "unit": "crates", "min": 380.0, "max": 520.0},
    "peppers": {"avg_price": 300.0, "unit": "bags", "min": 250.0, "max": 360.0},
    "maize": {"avg_price": 280.0, "unit": "bags", "min": 240.0, "max": 320.0},
}

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
# 5. AUTHENTICATION (Accepts both /login and /api/v1/login)
# ==============================================================================
@app.get("/")
def root():
    return {
        "status": "online",
        "platform": "AgriConnect Global API",
        "docs_url": "/docs",
    }

@app.post("/signup", response_model=Token)
@app.post("/api/v1/signup", response_model=Token)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    display_name = user_data.full_name or user_data.name or user_data.email.split("@")[0]
    user_location = user_data.location_or_region or user_data.location or "Accra"
    
    hashed_pw = get_password_hash(user_data.password)
    new_user = UserDB(
        email=user_data.email,
        hashed_password=hashed_pw,
        role=user_data.role or "buyer",
        full_name=display_name,
        location_or_region=user_location,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.email, "role": new_user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": new_user.role,
        "full_name": new_user.full_name,
    }

@app.post("/login", response_model=Token)
@app.post("/api/v1/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name,
    }

# ==============================================================================
# 6. PRODUCTS & ORDERS (Accepts direct and prefixed routes)
# ==============================================================================
@app.post("/products", response_model=ProductResponse)
@app.post("/api/v1/products", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    farmer_name = "Verified Local Farmer"
    farmer_id = None
    if token:
        user = get_current_user_from_token(token, db)
        if user:
            farmer_name = user.full_name
            farmer_id = user.id

    db_product = ProductDB(
        **product.model_dump(),
        farmer_name=farmer_name,
        farmer_id=farmer_id,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return ProductResponse(
        id=db_product.id,
        product_name=db_product.product_name,
        category=db_product.category,
        base_price_ghs=db_product.base_price_ghs,
        converted_price=db_product.base_price_ghs,
        currency="GHS",
        quantity_available=db_product.quantity_available,
        unit=db_product.unit,
        farmer_name=db_product.farmer_name,
        location=db_product.location,
        description=db_product.description,
    )

@app.get("/products", response_model=List[ProductResponse])
@app.get("/api/v1/products", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    currency: str = Query("GHS"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ProductDB)
    if category:
        query = query.filter(ProductDB.category.ilike(f"%{category}%"))
    if location:
        query = query.filter(ProductDB.location.ilike(f"%{location}%"))
    if search:
        query = query.filter(
            (ProductDB.product_name.ilike(f"%{search}%"))
            | (ProductDB.description.ilike(f"%{search}%"))
        )

    products = query.all()
    rate = EXCHANGE_RATES_TO_GHS.get(currency.upper(), 1.0)

    return [
        ProductResponse(
            id=p.id,
            product_name=p.product_name,
            category=p.category,
            base_price_ghs=p.base_price_ghs,
            converted_price=round(p.base_price_ghs * rate, 2),
            currency=currency.upper(),
            quantity_available=p.quantity_available,
            unit=p.unit,
            farmer_name=p.farmer_name,
            location=p.location,
            description=p.description,
        )
        for p in products
    ]

@app.post("/orders", response_model=OrderResponse)
@app.post("/api/v1/orders", response_model=OrderResponse)
def place_order(order: OrderCreate, db: Session = Depends(get_db)):
    product = db.query(ProductDB).filter(ProductDB.id == order.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.quantity_available < order.quantity:
        raise HTTPException(status_code=400, detail="Requested quantity exceeds stock")

    product.quantity_available -= order.quantity
    total_ghs = product.base_price_ghs * order.quantity
    curr = order.currency.upper()
    rate = EXCHANGE_RATES_TO_GHS.get(curr, 1.0)
    converted_total = round(total_ghs * rate, 2)

    new_order = OrderDB(
        product_id=order.product_id,
        buyer_name=order.buyer_name or "Anonymous Buyer",
        quantity=order.quantity,
        total_amount_ghs=total_ghs,
        target_currency=curr,
        converted_total=converted_total,
        status="PENDING_ESCROW",
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return OrderResponse(
        id=new_order.id,
        product_id=new_order.product_id,
        buyer_name=new_order.buyer_name,
        quantity=new_order.quantity,
        total_amount_ghs=new_order.total_amount_ghs,
        target_currency=new_order.target_currency,
        converted_total=new_order.converted_total,
        status=new_order.status,
        created_at=new_order.created_at,
    )

# ==============================================================================
# 7. LOGISTICS & OTP DISPATCH
# ==============================================================================
shipments_db: Dict[int, dict] = {}

@app.post("/logistics/dispatch/{order_id}")
@app.post("/api/v1/logistics/dispatch/{order_id}")
def initiate_dispatch(order_id: int, pickup: str = "Farm", dropoff: str = "Hub"):
    otp = str(random.randint(100000, 999999))
    now = datetime.utcnow().isoformat()
    shipments_db[order_id] = {
        "order_id": order_id,
        "status": "HARVESTING",
        "pickup_location": pickup,
        "dropoff_location": dropoff,
        "delivery_otp": otp,
        "updated_at": now,
        "timeline": [{"status": "HARVESTING", "location": pickup, "timestamp": now}],
    }
    return {"message": "Dispatch initiated", "order_id": order_id, "buyer_otp": otp}

@app.patch("/logistics/status/{order_id}")
@app.patch("/api/v1/logistics/status/{order_id}")
def update_shipment_status(order_id: int, update: DispatchUpdate):
    if order_id not in shipments_db:
        raise HTTPException(status_code=404, detail="Shipment not found")
    shipment = shipments_db[order_id]
    shipment["status"] = update.status
    shipment["current_location"] = update.current_location
    shipment["timeline"].append({
        "status": update.status,
        "location": update.current_location,
        "notes": update.driver_notes,
        "timestamp": datetime.utcnow().isoformat(),
    })
    return {"message": "Shipment updated", "shipment": shipment}

@app.post("/logistics/verify-delivery")
@app.post("/api/v1/logistics/verify-delivery")
def verify_delivery(data: DeliveryVerification, db: Session = Depends(get_db)):
    if data.order_id not in shipments_db:
        raise HTTPException(status_code=404, detail="Shipment not found")
    shipment = shipments_db[data.order_id]
    if shipment["delivery_otp"] != data.delivery_otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    shipment["status"] = "DELIVERED"
    order = db.query(OrderDB).filter(OrderDB.id == data.order_id).first()
    if order:
        order.status = "DELIVERED"
        db.commit()
    return {"status": "SUCCESS", "message": "Delivery verified and completed"}

# ==============================================================================
# 8. WEBSOCKET LIVE CHAT
# ==============================================================================
chat_rooms: Dict[int, List[WebSocket]] = {}

@app.websocket("/ws/chat/{order_id}/{user_name}")
async def websocket_chat(websocket: WebSocket, order_id: int, user_name: str):
    await websocket.accept()
    if order_id not in chat_rooms:
        chat_rooms[order_id] = []
    chat_rooms[order_id].append(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            for conn in chat_rooms[order_id]:
                await conn.send_json({
                    "sender": user_name,
                    "message": text,
                    "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                })
    except WebSocketDisconnect:
        chat_rooms[order_id].remove(websocket)

# ==============================================================================
# 9. SMART PRICING & MARKET INTELLIGENCE
# ==============================================================================
@app.get("/intelligence/price-advisory")
@app.get("/api/v1/intelligence/price-advisory")
def get_price_advisory(commodity: str, farmer_price: float, quantity: int = 1):
    key = commodity.lower().strip()
    benchmark = REGIONAL_BENCHMARKS.get(key)
    if not benchmark:
        return {"status": "NO_HISTORICAL_DATA", "message": "No benchmark data available"}
    
    avg = benchmark["avg_price"]
    diff_percent = round(((farmer_price - avg) / avg) * 100, 1)
    
    discount = 0
    if quantity >= 100:
        discount = 10
    elif quantity >= 50:
        discount = 5
        
    suggested_total = round((farmer_price * quantity) * (1 - discount / 100), 2)
    return {
        "commodity": commodity,
        "farmer_price": farmer_price,
        "regional_average": avg,
        "price_variance": f"{diff_percent}%",
        "benchmark_range": f"{benchmark['min']} - {benchmark['max']} GHS per {benchmark['unit']}",
        "bulk_analysis": {
            "order_quantity": quantity,
            "suggested_discount": f"{discount}%",
            "estimated_total_ghs": suggested_total,
        },
    }
