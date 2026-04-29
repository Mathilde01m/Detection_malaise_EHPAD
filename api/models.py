from sqlalchemy import Column, Integer, String, Float
from database import Base

class Resident(Base):
    __tablename__ = "residents"

    id = Column(Integer, primary_key=True)
    nom = Column(String)
    chambre = Column(String)
    secteur = Column(String)
    heart_rate = Column(Float)
    spo2 = Column(Float)
    risk_score = Column(Float)