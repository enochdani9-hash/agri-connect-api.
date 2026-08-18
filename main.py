from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from supabase import create_client, Client
import os

app = FastAPI(title="AgriConnect Production API", version="2.2")

# --- CORS VIP PASS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SUPABASE CONFIGURATION ---
SUPABASE_URL = "https://avchhgythvzkwclaebii.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DATA MODELS ---
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    farmer_name: str
    region: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProductCreateRequest(BaseModel):
    product_name: str
    category: str
    unit: str
    price_ghs: float
    quantity_available: int
    status: str = "Available Now"

class OrderRequest(BaseModel, extra="allow"):
    buyer_name: str
    buyer_phone: str
    item_id: int
    quantity_ordered: int
    delivery_option: str

@app.get("/")
def home():
    return {"message": "AgriConnect Production API is live with full Farmer Dashboard & Auth."}

# --- 1. FARMER SIGN-UP ---
@app.post("/api/v1/auth/signup")
def farmer_signup(data: SignupRequest):
    try:
        res = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "farmer_name": data.farmer_name,
                    "region": data.region
                }
            }
        })
        return {
            "status": "Success",
            "message": "Farmer account created successfully!",
            "user": res.user
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 2. FARMER LOGIN ---
@app.post("/api/v1/auth/login")
def farmer_login(data: LoginRequest):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
        return {
            "status": "Success",
            "access_token": res.session.access_token,
            "token_type": "bearer",
            "message": "Login successful!"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

# --- 3. GET ALL MARKETPLACE PRODUCTS ---
@app.get("/api/v1/products")
def get_products(category: Optional[str] = None):
    try:
        query = supabase.table("products").select("*")
        if category and category.lower() != "all":
            query = query.ilike("category", category)
        
        response = query.execute()
        return {"total_listings": len(response.data), "results": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. FARMER POST PRODUCT (PROTECTED) ---
@app.post("/api/v1/products")
def create_product(product: ProductCreateRequest, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token.")
    
    token = authorization.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        user_data = user_res.user
        if not user_data:
            raise HTTPException(status_code=401, detail="Unauthorized access.")
        
        metadata = user_data.user_metadata or {}
        farmer_name = metadata.get("farmer_name", "Verified Farmer")
        region = metadata.get("region", "Greater Accra")

        new_listing = {
            "farmer_name": farmer_name,
            "region": region,
            "category": product.category,
            "product_name": product.product_name,
            "unit": product.unit,
            "price_ghs": product.price_ghs,
            "quantity_available": product.quantity_available,
            "status": product.status
        }
        
        insert_res = supabase.table("products").insert(new_listing).execute()
        return {
            "status": "Success",
            "message": "Harvest listed live on the marketplace!",
            "listing": insert_res.data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 5. GET LOGGED-IN FARMER'S OWN LISTINGS ---
@app.get("/api/v1/farmer/my-listings")
def get_my_listings(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token.")
    
    token = authorization.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        user_data = user_res.user
        if not user_data:
            raise HTTPException(status_code=401, detail="Unauthorized access.")
        
        metadata = user_data.user_metadata or {}
        farmer_name = metadata.get("farmer_name")

        response = supabase.table("products").select("*").eq("farmer_name", farmer_name).execute()
        return {
            "farmer": farmer_name,
            "total_my_listings": len(response.data),
            "results": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 6. DELETE A LISTING ---
@app.delete("/api/v1/products/{product_id}")
def delete_product(product_id: int, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token.")
    
    token = authorization.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res.user:
            raise HTTPException(status_code=401, detail="Unauthorized access.")

        response = supabase.table("products").delete().eq("id", product_id).execute()
        return {
            "status": "Success",
            "message": f"Product ID {product_id} has been removed from the marketplace."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 7. PLACE AN ORDER ---
@app.post("/api/v1/order")
def create_order(order: OrderRequest):
    try:
        item_res = supabase.table("products").select("*").eq("id", order.item_id).execute()
        if not item_res.data:
            raise HTTPException(status_code=404, detail="Selected farm product not found.")
        
        item = item_res.data[0]
        if order.quantity_ordered > item["quantity_available"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Requested quantity exceeds available stock. Only {item['quantity_available']} {item['unit']}s left."
            )
        
        subtotal = order.quantity_ordered * float(item["price_ghs"])
        delivery_fee = 50.00 if order.delivery_option.lower() == "batch delivery" else 0.00
        grand_total = subtotal + delivery_fee
        
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
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
