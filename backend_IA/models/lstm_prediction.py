import numpy as np
import joblib
import os

# Chargement du modèle en mémoire au démarrage du backend
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'trained_model.pkl')
try:
    ai_model = joblib.load(MODEL_PATH)
    print("[IA] Modèle prédictif chargé avec succès.")
except Exception as e:
    print(f"[IA] Attention : Modèle non trouvé. L'entraînement a-t-il été fait ? Erreur: {e}")
    ai_model = None

def predict_malaise_risk(vitals_history):
    # Il faut au moins 5 mesures pour dégager une tendance
    if not ai_model or len(vitals_history) < 5:
        return 0
    
    # Récupération de l'historique
    hr_values = [v['hr'] for v in vitals_history]
    spo2_values = [v['spo2'] for v in vitals_history]
    
    # 1. Extraction des mêmes caractéristiques (Features) que lors de l'entraînement
    hr_mean = np.mean(hr_values)
    spo2_min = np.min(spo2_values)
    hr_trend = np.polyfit(range(len(hr_values)), hr_values, 1)[0]
    spo2_trend = np.polyfit(range(len(spo2_values)), spo2_values, 1)[0]
    
    features = np.array([[hr_mean, spo2_min, hr_trend, spo2_trend]])
    
    # 2. Prédiction par la VRAIE Intelligence Artificielle
    prediction = ai_model.predict(features)[0]
    
    return int(prediction) # Retourne 0 (Normal) ou 3 (Malaise)