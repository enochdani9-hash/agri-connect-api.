from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from supabase import create_client, Client
import os
import resend

app = FastAPI(title="AgriConnect Global API", version="3.0")

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
    country: str
    region: str
    phone: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class BuyerSignupRequest(BaseModel):
    email: EmailStr
    password: str
    buyer_name: str
    country: str
    phone: str
    location: str

class BuyerLoginRequest(BaseModel):
    email: EmailStr
    password: str

class OrderRequest(BaseModel, extra="allow"):
    buyer_name: str
    buyer_phone: str
    buyer_country: str
    buyer_location: str
    item_id: int
    quantity_ordered: int
    delivery_option: str

@app.get("/")
def home():
    return {"message": "AgriConnect Global API is live."}

# --- 1. FARMER SIGN-UP ---
@app.post("/api/v1/auth/signup")
def farmer_signup(data: SignupRequest):
    try:
        existing_users = supabase.auth.admin.list_users()
        for user in existing_users:
            if user.email.lower() == data.email.lower():
                raise HTTPException(status_code=400, detail="Email already registered.")

        res = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "role": "farmer",
                    "farmer_name": data.farmer_name,
                    "country": data.country,
                    "region": data.region,
                    "phone": data.phone
                }
            }
        })
        return {"status": "Success", "message": "Farmer account created globally!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 2. FARMER LOGIN ---
@app.post("/api/v1/auth/login")
def farmer_login(data: LoginRequest):
    try:
        res = supabase.auth.sign_in_with_password({"email": data.email, "password": data.password})
        return {"status": "Success", "access_token": res.session.access_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

# --- 3. BUYER SIGN-UP ---
@app.post("/api/v1/buyer/signup")
def buyer_signup(data: BuyerSignupRequest):
    try:
        existing_users = supabase.auth.admin.list_users()
        for user in existing_users:
            if user.email.lower() == data.email.lower():
                raise HTTPException(status_code=400, detail="Email already registered.")

        res = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "role": "buyer",
                    "buyer_name": data.buyer_name,
                    "country": data.country,
                    "phone": data.phone,
                    "location": data.location
                }
            }
        })
        return {"status": "Success", "message": "Buyer account created globally!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 4. BUYER LOGIN ---
@app.post("/api/v1/buyer/login")
def buyer_login(data: BuyerLoginRequest):
    try:
        res = supabase.auth.sign_in_with_password({"email": data.email, "password": data.password})
        return {"status": "Success", "access_token": res.session.access_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

# --- 5. GET GLOBAL PRODUCTS ---
@app.get("/api/v1/products")
def get_products(category: Optional[str] = None, search: Optional[str] = None):
    try:
        query = supabase.table("products").select("*")
        if category and category.lower() != "all":
            query = query.ilike("category", category)
        
        response = query.execute()
        data = response.data

        if search:
            s = search.lower()
            data = [
                item for item in data 
                if s in item["product_name"].lower() or s in item["category"].lower() or s in item.get("country", "").lower()
            ]

        return {"total_listings": len(data), "results": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 6. FARMER POST PRODUCT (GLOBAL) ---
@app.post("/api/v1/products")
async def create_product(
    product_name: str = Form(...),
    category: str = Form(...),
    unit: str = Form(...),
    price: float = Form(...),
    currency: str = Form(...),
    quantity_available: int = Form(...),
    status: str = Form("Available Now"),
    image: UploadFile = File(None),
    authorization: Optional[str] = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized access.")
    
    token = authorization.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        user_data = user_res.user
        metadata = user_data.user_metadata or {}
        
        farmer_name = metadata.get("farmer_name", "Global Farmer")
        region = metadata.get("region", "Global")
        country = metadata.get("country", "Unknown")
        farmer_email = metadata.get("email") or user_data.email

        image_url = "https://images.unsplash.com/photo-1595855759920-86582396756a?auto=format&fit=crop&w=600&q=80"
        if image:
            file_bytes = await image.read()
            file_path = f"{farmer_name.lower().replace(' ', '_')}_{image.filename}"
            supabase.storage.from_("product-images").upload(
                path=file_path, file=file_bytes, file_options={"content-type": image.content_type, "upsert": "true"}
            )
            image_url = supabase.storage.from_("product-images").get_public_url(file_path)

        new_listing = {
            "farmer_name": farmer_name,
            "region": region,
            "country": country,
            "category": category,
            "product_name": product_name,
            "unit": unit,
            "price": price,
            "currency": currency,
            "quantity_available": quantity_available,
            "status": status,
            "image_url": image_url,
            "farmer_email": farmer_email
        }
        
        insert_res = supabase.table("products").insert(new_listing).execute()
        return {"status": "Success", "listing": insert_res.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 7. GET MY LISTINGS ---
@app.get("/api/v1/farmer/my-listings")
def get_my_listings(authorization: Optional[str] = Header(None)):
    if not authorization: raise HTTPException(status_code=401)
    token = authorization.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        metadata = user_res.user.user_metadata or {}
        farmer_name = metadata.get("farmer_name", "")
        response = supabase.table("products").select("*").eq("farmer_name", farmer_name).execute()
        return {"farmer": farmer_name, "results": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 8. DELETE LISTING ---
@app.delete("/api/v1/products/{product_id}")
def delete_product(product_id: int, authorization: Optional[str] = Header(None)):
    if not authorization: raise HTTPException(status_code=401)
    try:
        supabase.table("products").delete().eq("id", product_id).execute()
        return {"status": "Success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 9. PLACE GLOBAL ORDER ---
@app.post("/api/v1/order")
def create_order(order: OrderRequest):
    try:
        item_res = supabase.table("products").select("*").eq("id", order.item_id).execute()
        if not item_res.data: raise HTTPException(status_code=404, detail="Product not found.")
        
        item = item_res.data[0]
        if order.quantity_ordered > item["quantity_available"]:
            raise HTTPException(status_code=400, detail="Exceeds stock.")
        
        subtotal = order.quantity_ordered * float(item["price"])
        # Global logistics flat fee integration marker (simplified for now)
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
            "buyer_country": order.buyer_country,
            "buyer_location": order.buyer_location,
            "quantity_ordered": order.quantity_ordered,
            "grand_total_amount": grand_total,
            "currency": item["currency"],
            "delivery_option": order.delivery_option
        }
        supabase.table("orders").insert(order_record).execute()
        return {"status": "Order Placed Successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 10. GET FARMER SALES ---
@app.get("/api/v1/farmer/sales")
def get_farmer_sales(authorization: Optional[str] = Header(None)):
    if not authorization: raise HTTPException(status_code=401)
    token = authorization.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        metadata = user_res.user.user_metadata or {}
        farmer_name = metadata.get("farmer_name", "")
        response = supabase.table("orders").select("*").eq("farmer_name", farmer_name).order("created_at", desc=True).execute()
        
        # Calculate revenue per currency dynamically
        revenue_map = {}
        for o in response.data:
            c = o.get("currency", "USD")
            revenue_map[c] = revenue_map.get(c, 0) + float(o["grand_total_amount"])

        return {
            "farmer": farmer_name,
            "total_orders": len(response.data),
            "revenue_by_currency": revenue_map,
            "orders": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
