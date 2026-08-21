class BuyerSignupRequest(BaseModel):
    email: EmailStr
    password: str
    buyer_name: str
    phone: str
    location: str

class BuyerLoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- BUYER SIGN-UP ---
@app.post("/api/v1/buyer/signup")
def buyer_signup(data: BuyerSignupRequest):
    try:
        existing_users = supabase.auth.admin.list_users()
        for user in existing_users:
            if user.email.lower() == data.email.lower():
                raise HTTPException(status_code=400, detail="This email address is already registered.")

        res = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "role": "buyer",
                    "buyer_name": data.buyer_name,
                    "phone": data.phone,
                    "location": data.location
                }
            }
        })
        return {"status": "Success", "message": "Buyer account created successfully!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- BUYER LOGIN ---
@app.post("/api/v1/buyer/login")
def buyer_login(data: BuyerLoginRequest):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
        return {
            "status": "Success",
            "access_token": res.session.access_token,
            "message": "Buyer login successful!"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid buyer email or password.")
