import random
from datetime import datetime
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

# ==============================================================================
# 1. DATABASE SETUP (SQLite + SQLAlchemy)
# ==============================================================================
DATABASE_URL = "sqlite:///./agriconnect.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_name = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)  # Poultry, Vegetables, Grains, etc.
    base_price_ghs = Column(Float, nullable=False)
    quantity_available = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)                 # crates, birds, kg, bags
    farmer_name = Column(String, nullable=False)
    location = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, nullable=False)
    buyer_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount_ghs = Column(Float, nullable=False)
    target_currency = Column(String, default="GHS")
    converted_total = Column(Float, nullable=False)
    status = Column(String, default="PENDING_ESCROW")  # PENDING_ESCROW, DISPATCHED, DELIVERED
    created_at = Column(DateTime, default=datetime.utcnow)


# Create tables on startup
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# 2. FASTAPI APPLICATION & CORS
# ==============================================================================
app = FastAPI(
    title="AgriConnect Global API",
    description="Full-stack AgTech engine with marketplace, logistics OTP, live chat, and smart pricing.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 3. STATIC RATES & MARKET BENCHMARKS
# ==============================================================================
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

# ==============================================================================
# 4. PYDANTIC SCHEMAS
# ==============================================================================
class ProductCreate(BaseModel):
    product_name: str = Field(..., example="Fresh Farm Broilers")
    category: str = Field(..., example="Poultry")
    base_price_ghs: float = Field(..., gt=0, example=120.00)
    quantity_available: int = Field(..., ge=1, example=100)
    unit: str = Field(..., example="birds")
    farmer_name: str = Field(..., example="Daniels Farms")
    location: str = Field(..., example="Accra")
    description: Optional[str] = Field(None, example="Organic farm-raised broilers.")


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
    created_at: datetime


class OrderCreate(BaseModel):
    product_id: int
    buyer_name: str
    quantity: int = Field(..., gt=0)
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
    status: str  # HARVESTING, IN_TRANSIT, ARRIVED_AT_HUB, OUT_FOR_DELIVERY, DELIVERED
    current_location: str
    driver_notes: Optional[str] = None


class DeliveryVerification(BaseModel):
    order_id: int
    delivery_otp: str


# ==============================================================================
# 5. CORE MARKETPLACE ENDPOINTS
# ==============================================================================
@app.get("/")
def root():
    return {
        "status": "online",
        "platform": "AgriConnect Global API v2.0",
        "docs_url": "/docs",
        "modules": ["Marketplace", "Logistics & OTP", "Live Chat", "Smart Pricing"],
    }


@app.post(
    "/api/v1/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Marketplace"],
)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = ProductDB(**product.model_dump())
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
        created_at=db_product.created_at,
    )


@app.get(
    "/api/v1/products",
    response_model=List[ProductResponse],
    tags=["Marketplace"],
)
def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    currency: str = Query("GHS", description="Target currency: GHS, USD, EUR, GBP, NGN, XOF"),
    search: Optional[str] = Query(None, description="Search product name or description"),
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
            created_at=p.created_at,
        )
        for p in products
    ]


@app.post(
    "/api/v1/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Orders"],
)
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
        buyer_name=order.buyer_name,
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
# 6. MODULE 3: LOGISTICS & DISPATCH WITH OTP VERIFICATION
# ==============================================================================
shipments_db: Dict[int, dict] = {}


@app.post("/api/v1/logistics/dispatch/{order_id}", tags=["Logistics & Dispatch"])
def initiate_dispatch(
    order_id: int,
    pickup_location: str,
    dropoff_location: str,
    db: Session = Depends(get_db),
):
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    otp = str(random.randint(100000, 999999))
    now = datetime.utcnow().isoformat()

    shipments_db[order_id] = {
        "order_id": order_id,
        "status": "HARVESTING",
        "pickup_location": pickup_location,
        "dropoff_location": dropoff_location,
        "current_location": pickup_location,
        "delivery_otp": otp,
        "updated_at": now,
        "timeline": [{"status": "HARVESTING", "location": pickup_location, "timestamp": now}],
    }

    order.status = "DISPATCHED"
    db.commit()

    return {
        "message": "Dispatch initiated successfully",
        "order_id": order_id,
        "buyer_otp": otp,
        "status": "HARVESTING",
    }


@app.patch("/api/v1/logistics/status/{order_id}", tags=["Logistics & Dispatch"])
def update_shipment_status(order_id: int, update: DispatchUpdate):
    if order_id not in shipments_db:
        raise HTTPException(status_code=404, detail="Shipment record not found")

    shipment = shipments_db[order_id]
    shipment["status"] = update.status
    shipment["current_location"] = update.current_location
    shipment["updated_at"] = datetime.utcnow().isoformat()
    shipment["timeline"].append(
        {
            "status": update.status,
            "location": update.current_location,
            "notes": update.driver_notes,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    return {"message": "Shipment updated", "shipment": shipment}


@app.post("/api/v1/logistics/verify-delivery", tags=["Logistics & Dispatch"])
def verify_delivery(data: DeliveryVerification, db: Session = Depends(get_db)):
    if data.order_id not in shipments_db:
        raise HTTPException(status_code=404, detail="Shipment record not found")

    shipment = shipments_db[data.order_id]
    if shipment["delivery_otp"] != data.delivery_otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code. Delivery verification failed.")

    shipment["status"] = "DELIVERED"
    now = datetime.utcnow().isoformat()
    shipment["timeline"].append(
        {"status": "DELIVERED", "location": shipment["dropoff_location"], "timestamp": now}
    )

    order = db.query(OrderDB).filter(OrderDB.id == data.order_id).first()
    if order:
        order.status = "DELIVERED"
        db.commit()

    return {
        "status": "SUCCESS",
        "message": "OTP verified. Escrow payment released to farmer account.",
        "order_id": data.order_id,
    }


# ==============================================================================
# 7. MODULE 4: REAL-TIME WEBSOCKET BUYER-FARMER CHAT
# ==============================================================================
class ConnectionManager:
    def __init__(self):
        self.active_rooms: Dict[int, List[WebSocket]] = {}

    async def connect(self, order_id: int, websocket: WebSocket):
        await websocket.accept()
        if order_id not in self.active_rooms:
            self.active_rooms[order_id] = []
        self.active_rooms[order_id].append(websocket)

    def disconnect(self, order_id: int, websocket: WebSocket):
        if order_id in self.active_rooms:
            if websocket in self.active_rooms[order_id]:
                self.active_rooms[order_id].remove(websocket)
            if not self.active_rooms[order_id]:
                del self.active_rooms[order_id]

    async def broadcast(self, order_id: int, message: dict):
        if order_id in self.active_rooms:
            for connection in self.active_rooms[order_id]:
                await connection.send_json(message)


chat_manager = ConnectionManager()


@app.websocket("/ws/chat/{order_id}/{user_name}")
async def websocket_chat(websocket: WebSocket, order_id: int, user_name: str):
    await chat_manager.connect(order_id, websocket)
    await chat_manager.broadcast(
        order_id,
        {
            "sender": "System",
            "message": f"{user_name} has joined the negotiation room.",
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        },
    )
    try:
        while True:
            text = await websocket.receive_text()
            await chat_manager.broadcast(
                order_id,
                {
                    "sender": user_name,
                    "message": text,
                    "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                },
            )
    except WebSocketDisconnect:
        chat_manager.disconnect(order_id, websocket)
        await chat_manager.broadcast(
            order_id,
            {
                "sender": "System",
                "message": f"{user_name} left the chat.",
                "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
            },
        )


# ==============================================================================
# 8. MODULE 5: SMART PRICING & MARKET INTELLIGENCE
# ==============================================================================
@app.get("/api/v1/intelligence/price-advisory", tags=["Market Intelligence"])
def get_price_advisory(commodity: str, farmer_price: float, quantity: int = 1):
    key = commodity.lower().strip()
    benchmark = REGIONAL_BENCHMARKS.get(key)

    if not benchmark:
        return {
            "commodity": commodity,
            "status": "NO_HISTORICAL_DATA",
            "message": "No regional price data available for this commodity.",
        }

    avg = benchmark["avg_price"]
    diff_percent = round(((farmer_price - avg) / avg) * 100, 1)

    if diff_percent < -10:
        verdict = "High Demand (Priced below market average)"
    elif -10 <= diff_percent <= 10:
        verdict = "Competitive (Fair market price)"
    else:
        verdict = "Premium (Above regional average)"

    discount_percent = 0
    if quantity >= 100:
        discount_percent = 10
    elif quantity >= 50:
        discount_percent = 5

    suggested_bulk_total = round((farmer_price * quantity) * (1 - discount_percent / 100), 2)

    return {
        "commodity": commodity,
        "farmer_price": farmer_price,
        "regional_average": avg,
        "benchmark_range": f"{benchmark['min']} - {benchmark['max']} GHS per {benchmark['unit']}",
        "price_variance": f"{diff_percent}%",
        "market_verdict": verdict,
        "bulk_pricing": {
            "order_quantity": quantity,
            "suggested_discount": f"{discount_percent}%",
            "estimated_total_ghs": suggested_bulk_total,
        },
    }
