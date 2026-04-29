from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import SessionLocal

app = FastAPI(title="API EHPAD")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "API EHPAD active"}


@app.get("/residents")
def get_residents():
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


@app.get("/health")
def health_check():
    return {"status": "ok"}