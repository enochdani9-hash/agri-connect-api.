from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="AgriConnect API", version="1.0")

# --- CORS VIP PASS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- IN-MEMORY DATABASE (Simulated Local Farm Inventory) ---
# In a production app, this would connect to a database. For our zero-cash MVP, this works instantly!
inventory_db = [
    {
        "item_id": 1,
        "farmer_name": "Kofi Mensah",
        "region": "Greater Accra",
        "category": "Vegetables",
        "product_name": "Fresh Tomatoes",
        "unit": "Crate",
        "price_ghs": 450.00,
        "quantity_available": 35,
        "status": "Ready for Harvest"
    },
    {
        "item_id": 2,
        "farmer_name": "Ama Serwaa",
        "region": "Ashanti",
        "category": "Poultry",
        "product_name": "Broilers (Dressed)",
        "unit": "Piece",
        "price_ghs": 95.00,
        "quantity_available": 120,
        "status": "Available Now"
    },
    {
        "item_id": 3,
        "farmer_name": "Yaw Boateng",
        "region": "Eastern Region",
        "category": "Vegetables",
        "product_name": "Bell Peppers (Green & Red)",
        "unit": "Bag",
        "price_ghs": 600.00,
        "quantity_available": 15,
        "status": "Ready for Harvest"
    },
    {
        "item_id": 4,
        "farmer_name": "Esi Appiah",
        "region": "Central Region",
        "category": "Tubers",
        "product_name": "Puna Yam",
        "unit": "Tuber",
        "price_ghs": 35.00,
        "quantity_available": 300,
        "status": "Available Now"
    }
]

# Order Data Model
class OrderRequest(BaseModel, extra="allow"):
    buyer_name: str
    buyer_phone: str
    item_id: int
    quantity_ordered: int
    delivery_option: str # Options: "Farm Pickup", "Batch Delivery"

@app.get("/")
def home():
    return {"message": "Welcome to the AgriConnect API. Local supply chain engine is live."}

# --- GET ALL PRODUCTS OR FILTER BY CATEGORY ---
@app.get("/api/v1/products")
def get_products(category: Optional[str] = None):
    if category:
        filtered = [item for item in inventory_db if item["category"].lower() == category.lower()]
        return {"category_filter": category, "results": filtered}
    return {"total_listings": len(inventory_db), "results": inventory_db}

# --- PLACE AN ORDER & CALCULATE FULFILLMENT ---
@app.post("/api/v1/order")
def create_order(order: OrderRequest):
    # Find the item in inventory
    item = next((i for i in inventory_db if i["item_id"] == order.item_id), None)
    
    if not item:
        raise HTTPException(status_code=404, detail="Selected farm product not found.")
    
    if order.quantity_ordered > item["quantity_available"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Requested quantity exceeds available stock. Only {item['quantity_available']} {item['unit']}s left."
        )
    
    # Calculate total cost
    subtotal = order.quantity_ordered * item["price_ghs"]
    
    # Calculate logistics/handling fee based on fulfillment choice
    delivery_fee = 0.00
    if order.delivery_option.lower() == "batch delivery":
        delivery_fee = 50.00 # Flat community batch delivery fee
    
    grand_total = subtotal + delivery_fee
    
    # Deduct stock (Simulating live transaction update)
    item["quantity_available"] -= order.quantity_ordered
    
    return {
        "status": "Order Successfully Placed",
        "order_summary": {
            "product": item["product_name"],
            "farmer": item["farmer_name"],
            "quantity": order.quantity_ordered,
            "unit": item["unit"],
            "subtotal_ghs": f"GH₵ {subtotal:,.2f}",
            "fulfillment_type": order.delivery_option,
            "delivery_fee_ghs": f"GH₵ {delivery_fee:,.2f}",
            "grand_total_ghs": f"GH₵ {grand_total:,.2f}"
        },
        "next_steps": "The farmer and local dispatch have been notified via automated routing."
    }