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
        prediction = self.rf_fall.predict(features)
        return 1 if prediction[0] == 1 else 0

    def predict_vitals_anomaly(self, vitals_sequence):
        if not hasattr(self, 'lstm_vitals'):
            return 0.0
        try:
            import numpy as np
            arr = np.array(vitals_sequence).reshape(1, len(vitals_sequence), -1)
            score = float(self.lstm_vitals.predict(arr, verbose=0)[0][0])
            return score
        except Exception:
            return 0.0


# Instance globale importée par processor.py
ai = EHPAD_AI_Engine()