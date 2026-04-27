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
            print(f"[!] Erreur critique lors du chargement des modèles : {e}")

    def predict_ambient_anomaly(self, ambient_data):
        # Retourne 1 si anomalie, 0 si normal
        features = np.array([[ambient_data['activity'], ambient_data['light'], ambient_data['noise']]])
        prediction = self.iso_forest.predict(features)
        return 1 if prediction[0] == -1 else 0

    def predict_fall(self, accel_data):
        # Retourne 1 si chute détectée
        features = np.array([[accel_data['x'], accel_data['y'], accel_data['z']]])
        return self.rf_fall.predict(features)[0]

    def predict_vitals_risk(self, history):
        # Historique doit contenir 10 éléments
        if len(history) < 10:
            return 0
        
        # Transformation en tenseur 3D pour le LSTM : (1, 10, 2)
        seq = [[v['hr'], v['spo2']] for v in history]
        features = np.array([seq], dtype=np.float32)
        
        prediction = self.lstm_vitals.predict(features, verbose=0)[0][0]
        # Si probabilité > 70%, on déclenche l'alerte
        return 1 if prediction > 0.7 else 0

# Instance globale
ai = EHPAD_AI_Engine()