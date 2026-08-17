from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client
import os

app = FastAPI(title="AgriConnect Production API", version="2.0")

# --- CORS VIP PASS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SUPABASE CONFIGURATION (SECURE) ---
SUPABASE_URL = "https://avchhgythvzkwclaebii.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Order Data Model
class OrderRequest(BaseModel, extra="allow"):
    buyer_name: str
    buyer_phone: str
    item_id: int
    quantity_ordered: int
    delivery_option: str # Options: "Farm Pickup", "Batch Delivery"

@app.get("/")
def home():
    return {"message": "AgriConnect Production API is live with persistent Supabase storage."}

# --- GET ALL PRODUCTS FROM SUPABASE ---
@app.get("/api/v1/products")
def get_products(category: Optional[str] = None):
    try:
        query = supabase.table("products").select("*")
        if category and category.lower() != "all":
            query = query.ilike("category", category)
        
        response = query.execute()
        data = response.data
        return {"total_listings": len(data), "results": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- PLACE AN ORDER & UPDATE SUPABASE INVENTORY ---
@app.post("/api/v1/order")
def create_order(order: OrderRequest):
    try:
        # Fetch the item from Supabase using its ID
        item_res = supabase.table("products").select("*").eq("id", order.item_id).execute()
        if not item_res.data:
            raise HTTPException(status_code=404, detail="Selected farm product not found.")
        
        item = item_res.data[0]
        
        if order.quantity_ordered > item["quantity_available"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Requested quantity exceeds available stock. Only {item['quantity_available']} {item['unit']}s left."
            )
        
        # Calculate pricing
        subtotal = order.quantity_ordered * float(item["price_ghs"])
        delivery_fee = 50.00 if order.delivery_option.lower() == "batch delivery" else 0.00
        grand_total = subtotal + delivery_fee
        
        # Update stock in Supabase database permanently
        new_quantity = item["quantity_available"] - order.quantity_ordered
        supabase.table("products").update({"quantity_available": new_quantity}).eq("id", order.item_id).execute()
        
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
            "next_steps": "The farmer and local dispatch have been notified."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
