from dataclasses import dataclass


@dataclass
class Resident:
    resident_id: str
    age: int
    pathologie: str
    mobilite: str
    risque_principal: str
    heart_rate: int
    spo2: int
    systolic_bp: int
    diastolic_bp: int
    temperature: float
    glucose: int