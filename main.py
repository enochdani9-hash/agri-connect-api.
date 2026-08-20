# --- UPDATE THE ORDER REQUEST MODEL ---
class OrderRequest(BaseModel, extra="allow"):
    buyer_name: str
    buyer_phone: str
    item_id: int
    quantity_ordered: int
    delivery_option: str

# --- 7. PLACE AN ORDER & SAVE TO ORDERS TABLE ---
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
        
        # Update stock
        new_quantity = item["quantity_available"] - order.quantity_ordered
        supabase.table("products").update({"quantity_available": new_quantity}).eq("id", order.item_id).execute()
        
        # Save order to database history
        order_record = {
            "item_id": order.item_id,
            "product_name": item["product_name"],
            "farmer_name": item["farmer_name"],
            "buyer_name": order.buyer_name,
            "buyer_phone": order.buyer_phone,
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
        farmer_name = metadata.get("farmer_name")

        # Fetch all orders matching this farmer's name
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
