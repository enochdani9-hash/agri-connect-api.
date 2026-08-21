from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from supabase import create_client, Client
import os
import resend

app = FastAPI(title="AgriConnect Production API", version="2.12")

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

# --- RESEND EMAIL CONFIGURATION ---
resend.api_key = os.getenv("RESEND_API_KEY", "re_YOUR_RESEND_API_KEY_HERE")

# --- DATA MODELS ---
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    farmer_name: str
    region: str
    phone: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class OrderRequest(BaseModel, extra="allow"):
    buyer_name: str
    buyer_phone: str
    buyer_location: Optional[str] = "Accra"
    item_id: int
    quantity_ordered: int
    delivery_option: str

@app.get("/")
def home():
    return {"message": "AgriConnect Production API is live with Buyer Location & Advanced Search Support."}

# --- 1. FARMER SIGN-UP (Strict Duplicate Block via Admin Check) ---
@app.post("/api/v1/auth/signup")
def farmer_signup(data: SignupRequest):
    try:
        existing_users = supabase.auth.admin.list_users()
        for user in existing_users:
            if user.email.lower() == data.email.lower():
                raise HTTPException(status_code=400, detail="This email address is already registered. Please sign in instead.")

        res = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "farmer_name": data.farmer_name,
                    "region": data.region,
                    "phone": data.phone,
                    "email": data.email
                }
            }
        })
            
        return {
            "status": "Success",
            "message": "Farmer account created successfully!",
            "user": res.user
        }
    except HTTPException as he:
        raise he
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

# --- 3. GET ALL MARKETPLACE PRODUCTS WITH SEARCH ---
@app.get("/api/v1/products")
def get_products(category: Optional[str] = None, search: Optional[str] = None):
    try:
        query = supabase.table("products").select("*")
        if category and category.lower() != "all":
            query = query.ilike("category", category)
        
        response = query.execute()
        data = response.data

        # Filter by search term locally if provided (matches English or Ghanaian local names)
        if search:
            s = search.lower()
            data = [
                item for item in data 
                if s in item["product_name"].lower() or s in item["category"].lower() or s in item.get("region", "").lower()
            ]

        return {"total_listings": len(data), "results": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. FARMER POST PRODUCT WITH PROPER METADATA EXTRACTION ---
@app.post("/api/v1/products")
async def create_product(
    product_name: str = Form(...),
    category: str = Form(...),
    unit: str = Form(...),
    price_ghs: float = Form(...),
    quantity_available: int = Form(...),
    status: str = Form("Available Now"),
    image: UploadFile = File(None),
    authorization: Optional[str] = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token.")
    
    token = authorization.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        user_data = user_res.user
        if not user_data:
            raise HTTPException(status_code=401, detail="Unauthorized access.")
        
        metadata = user_data.user_metadata or {}
        farmer_name = metadata.get("farmer_name") or user_data.email.split("@")[0]
        region = metadata.get("region", "Greater Accra")
        farmer_email = metadata.get("email") or user_data.email

        image_url = "https://images.unsplash.com/photo-1595855759920-86582396756a?auto=format&fit=crop&w=600&q=80"

        if image:
            file_bytes = await image.read()
            file_path = f"{farmer_name.lower().replace(' ', '_')}_{image.filename}"
            
            supabase.storage.from_("product-images").upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": image.content_type, "upsert": "true"}
            )
            
            public_url_res = supabase.storage.from_("product-images").get_public_url(file_path)
            image_url = public_url_res

        new_listing = {
            "farmer_name": farmer_name,
            "region": region,
            "category": category,
            "product_name": product_name,
            "unit": unit,
            "price_ghs": price_ghs,
            "quantity_available": quantity_available,
            "status": status,
            "image_url": image_url,
            "farmer_email": farmer_email
        }
        
        insert_res = supabase.table("products").insert(new_listing).execute()
        return {
            "status": "Success",
            "message": "Harvest listed live with image on the marketplace!",
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
        farmer_name = metadata.get("farmer_name") or user_data.email.split("@")[0]

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

# --- 7. PLACE AN ORDER & SAVE RECORD (With Buyer Location) ---
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
        
        order_record = {
            "item_id": order.item_id,
            "product_name": item["product_name"],
            "farmer_name": item["farmer_name"],
            "buyer_name": order.buyer_name,
            "buyer_phone": order.buyer_phone,
            "buyer_location": order.buyer_location,
            "quantity_ordered": order.quantity_ordered,
            "grand_total": grand_total,
            "delivery_option": order.delivery_option
        }
        supabase.table("orders").insert(order_record).execute()

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

# --- 8. GET FARMER SALES HISTORY & REVENUE ---
@app.get("/api/v1/farmer/sales")
def get_farmer_sales(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token.")
    
    token = authorization.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        user_data = user_res.user
        if not user_data:
            raise HTTPException(status_code=401, detail="Unauthorized access.")
        
        metadata = user_data.user_metadata or {}
        farmer_name = metadata.get("farmer_name") or user_data.email.split("@")[0]

        response = supabase.table("orders").select("*").eq("farmer_name", farmer_name).order("created_at", desc=True).execute()
        orders = response.data
        total_revenue = sum(float(o["grand_total"]) for o in orders)

        return {
            "farmer": farmer_name,
            "total_orders": len(orders),
            "total_revenue_ghs": total_revenue,
            "orders": orders
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
