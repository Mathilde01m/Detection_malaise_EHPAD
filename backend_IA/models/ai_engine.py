import joblib
import numpy as np
import tensorflow as tf
import os

MODELS_DIR = os.path.dirname(__file__)

class EHPAD_AI_Engine:
    def __init__(self):
        print("[IA] Chargement des modèles en mémoire...")
        try:
            self.iso_forest = joblib.load(os.path.join(MODELS_DIR, 'iso_ambient.pkl'))
            self.rf_fall = joblib.load(os.path.join(MODELS_DIR, 'rf_fall.pkl'))
            self.lstm_vitals = tf.keras.models.load_model(os.path.join(MODELS_DIR, 'lstm_vitals.keras'))
            print("[IA] Les 3 modèles (LSTM, RF, IF) sont opérationnels.")
        except Exception as e:
            print(f"[!] Modèles non disponibles (pas encore entraînés) : {e}")
            print("[!] L'IA fonctionne en mode dégradé — détection par seuils uniquement.")

    def predict_ambient_anomaly(self, ambient_data):
        if not hasattr(self, 'iso_forest'):
            return 0
        features = np.array([[ambient_data['activity'], ambient_data['light'], ambient_data['noise']]])
        prediction = self.iso_forest.predict(features)
        return 1 if prediction[0] == -1 else 0

    def predict_fall(self, accel_data):
        if not hasattr(self, 'rf_fall'):
            return 0
        features = np.array([[accel_data['x'], accel_data['y'], accel_data['z']]])
        return self.rf_fall.predict(features)[0]

    def predict_vitals_risk(self, history):
        if not hasattr(self, 'lstm_vitals'):
            return 0
        if len(history) < 10:
            return 0
        seq = [[v.get('heart_rate', v.get('hr', 0)), v.get('spo2', 0)] for v in history]
        features = np.array([seq], dtype=np.float32)
        prediction = self.lstm_vitals.predict(features, verbose=0)[0][0]
        return 1 if prediction > 0.7 else 0

# Instance globale
ai = EHPAD_AI_Engine()