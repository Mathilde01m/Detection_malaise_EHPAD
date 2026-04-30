from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.hash import bcrypt
from datetime import datetime, timedelta

from database import SessionLocal

app = FastAPI(title="API EHPAD")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "ehpad_secret_key_demo_2024"
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 8

security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str

def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

def verify_password(plain: str, stored_hash: str) -> bool:
    if stored_hash == "hashed_password_demo":
        return plain == "Demo1234!"
    try:
        return bcrypt.verify(plain, stored_hash)
    except Exception:
        return False

@app.get("/")
def home():
    return {"message": "API EHPAD active"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/login")
def login(body: LoginRequest):
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT id, firstname, lastname, email, password_hash, role FROM users WHERE email = :e AND is_active = TRUE"),
            {"e": body.email}
        ).fetchone()

        print(f"[LOGIN] email reçu='{body.email}' | user trouvé={row is not None} | hash={row.password_hash if row else 'N/A'}")
        if not row or not verify_password(body.password, row.password_hash):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

        db.execute(text("UPDATE users SET last_login = NOW() WHERE id = :id"), {"id": row.id})
        db.commit()

        token = create_token({
            "user_id": row.id,
            "email":   row.email,
            "role":    row.role,
            "name":    f"{row.firstname} {row.lastname}"
        })

        return {
            "token": token,
            "role":  row.role,
            "name":  f"{row.firstname} {row.lastname}",
            "email": row.email
        }
    finally:
        db.close()

@app.get("/me")
def get_me(user = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "email":   user["email"],
        "role":    user["role"],
        "name":    user["name"]
    }

@app.get("/residents")
def get_residents(user = Depends(get_current_user)):
    if user["role"] == "family":
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT resident_id, room, zone, heart_rate, spo2, temperature, ai_risk_score
            FROM dashboard_global_view
            ORDER BY room
        """)).fetchall()

        result = []
        for r in rows:
            secteur = "A" if r.zone == "Aile A" else ("B" if r.zone == "Aile B" else r.zone)
            result.append({
                "id":          r.resident_id,
                "nom":         f"Résident {r.resident_id}",
                "chambre":     r.room,
                "secteur":     secteur,
                "heart_rate":  r.heart_rate,
                "spo2":        r.spo2,
                "temperature": r.temperature,
                "risk_score":  r.ai_risk_score,
                "tension":     "--/--"
            })
        return result
    finally:
        db.close()

@app.get("/my-resident")
def get_my_resident(user = Depends(get_current_user)):
    if user["role"] != "family":
        raise HTTPException(status_code=403, detail="Réservé aux comptes famille")

    db = SessionLocal()
    try:
        access = db.execute(
            text("""
                SELECT fa.resident_id, fa.relationship,
                       r.room, r.heart_rate, r.spo2, r.temperature, r.ai_risk_score
                FROM family_access fa
                JOIN dashboard_global_view r ON r.resident_id = fa.resident_id
                WHERE fa.user_id = :uid
            """),
            {"uid": user["user_id"]}
        ).fetchone()

        if not access:
            raise HTTPException(status_code=404, detail="Aucun résident associé à ce compte")

        return {
            "id":           access.resident_id,
            "nom":          f"Résident {access.resident_id}",
            "chambre":      access.room,
            "relationship": access.relationship,
            "heart_rate":   access.heart_rate,
            "spo2":         access.spo2,
            "temperature":  access.temperature,
            "risk_score":   access.ai_risk_score,
        }
    finally:
        db.close()