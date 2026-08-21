# --- 1. FARMER SIGN-UP (Strict Duplicate Block via Admin check) ---
@app.post("/api/v1/auth/signup")
def farmer_signup(data: SignupRequest):
    try:
        # Check if the email already exists in Supabase auth list
        existing_users = supabase.auth.admin.list_users()
        for user in existing_users:
            if user.email.lower() == data.email.lower():
                raise HTTPException(status_code=400, detail="This email address is already registered. Please sign in instead.")

        res = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "farmer_name": data.data.farmer_name if hasattr(data, 'data') else data.farmer_name,
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
