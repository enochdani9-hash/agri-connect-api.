# --- 1. FARMER SIGN-UP (Strict Duplicate Block) ---
@app.post("/api/v1/auth/signup")
def farmer_signup(data: SignupRequest):
    try:
        # Attempt signup
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
        
        # If Supabase returns an identity list that is empty, it means the email is already taken
        if res.user and res.user.identities and len(res.user.identities) == 0:
            raise HTTPException(status_code=400, detail="An account with this email address already exists.")
            
        return {
            "status": "Success",
            "message": "Farmer account created successfully!",
            "user": res.user
        }
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "user already registered" in error_msg.lower() or "identity" in error_msg.lower():
            raise HTTPException(status_code=400, detail="This email address is already registered. Please sign in instead.")
        raise HTTPException(status_code=400, detail=error_msg)
