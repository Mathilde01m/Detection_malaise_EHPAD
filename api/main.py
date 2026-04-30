from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import text
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta

from database import SessionLocal

# ── Configuration JWT ─────────────────────────────────────────────────────────
SECRET_KEY = "ehpad_secret_key_2024"
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 8

# ── Bcrypt context ─────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

app = FastAPI(title="API EHPAD")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modèles Pydantic ───────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


# ── Helpers auth ───────────────────────────────────────────────────────────────
def verify_password(plain: str, stored_hash: str) -> bool:
    """Accepte 'hashed_password_demo' comme mot de passe demo (Demo1234!)."""
    if stored_hash == "hashed_password_demo":
        return plain == "Demo1234!"
    try:
        return pwd_context.verify(plain, stored_hash)
    except Exception:
        return False


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


# ── Routes publiques ───────────────────────────────────────────────────────────
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
            text("SELECT id, email, role, password_hash, firstname, lastname FROM users WHERE email = :email"),
            {"email": body.email}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

        if not verify_password(body.password, row.password_hash):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

        full_name = f"{row.firstname or ''} {row.lastname or ''}".strip() or row.email

        token = create_token({
            "sub": str(row.id),
            "email": row.email,
            "role": row.role,
            "name": full_name,
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": row.role,
            "name": full_name,
        }
    finally:
        db.close()


# ── Route info utilisateur connecté ───────────────────────────────────────────
@app.get("/me")
def get_me(user=Depends(get_current_user)):
    return {
        "id": user.get("sub"),
        "email": user.get("email"),
        "role": user.get("role"),
        "name": user.get("name"),
    }


# ── Route staff : tous les résidents ──────────────────────────────────────────
@app.get("/residents")
def get_residents(user=Depends(get_current_user)):
    if user.get("role") == "family":
        raise HTTPException(status_code=403, detail="Accès réservé au personnel")

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT
                resident_id,
                room,
                zone,
                heart_rate,
                spo2,
                temperature,
                ai_risk_score
            FROM dashboard_global_view
            ORDER BY room
        """)).fetchall()

        result = []
        for r in rows:
            if r.zone == "Aile A":
                secteur = "A"
            elif r.zone == "Aile B":
                secteur = "B"
            else:
                secteur = r.zone

            result.append({
                "id": r.resident_id,
                "nom": f"Résident {r.resident_id}",
                "chambre": r.room,
                "secteur": secteur,
                "heart_rate": r.heart_rate,
                "spo2": r.spo2,
                "temperature": r.temperature,
                "risk_score": r.ai_risk_score,
                "tension": "--/--"
            })

        return result
    finally:
        db.close()


# ── Route famille : seulement leur résident ───────────────────────────────────
@app.get("/my-resident")
def get_my_resident(user=Depends(get_current_user)):
    if user.get("role") != "family":
        raise HTTPException(status_code=403, detail="Accès réservé aux familles")

    db = SessionLocal()
    try:
        row = db.execute(text("""
            SELECT
                d.resident_id,
                d.room,
                d.zone,
                d.heart_rate,
                d.spo2,
                d.temperature,
                d.ai_risk_score,
                fa.relationship
            FROM family_access fa
            JOIN dashboard_global_view d ON d.resident_id = fa.resident_id
            WHERE fa.user_id = :uid
            LIMIT 1
        """), {"uid": user.get("sub")}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Aucun résident associé à ce compte")

        return {
            "id": row.resident_id,
            "nom": f"Résident {row.resident_id}",
            "chambre": row.room,
            "secteur": row.zone,
            "heart_rate": row.heart_rate,
            "spo2": row.spo2,
            "temperature": row.temperature,
            "risk_score": row.ai_risk_score,
            "tension": "--/--",
            "relationship": row.relationship or ""
        }
    finally:
        db.close()
