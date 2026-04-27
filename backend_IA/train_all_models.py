import numpy as np
import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import tensorflow as tf

# Pour éviter les logs superflus de TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

models_dir = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(models_dir, exist_ok=True)

print("[1/3] Entraînement de l'Isolation Forest (Capteurs Ambiants)...")
# Données normales : Mouvement modéré, lumière normale, bruit modéré
# Anomalies : Reste 3h dans la salle de bain, agitation nocturne
X_ambient_normal = np.random.normal(loc=[5, 50, 30], scale=[2, 10, 5], size=(2000, 3))
X_ambient_anomalies = np.random.uniform(low=[0, 0, 0], high=[10, 100, 80], size=(100, 3))
X_ambient = np.vstack([X_ambient_normal, X_ambient_anomalies])

iso_forest = IsolationForest(contamination=0.05, random_state=42)
iso_forest.fit(X_ambient)
joblib.dump(iso_forest, os.path.join(models_dir, 'iso_ambient.pkl'))

print("[2/3] Entraînement du Random Forest (Détection de Chute)...")
# X, Y, Z de l'accéléromètre. 
# Normal = G=9.8 sur un axe. Chute = pic brutal sur les axes.
X_accel = []
y_accel = []
for _ in range(3000):
    if np.random.rand() > 0.1: # 90% normal
        X_accel.append([np.random.normal(0, 1), np.random.normal(0, 1), np.random.normal(9.8, 1)])
        y_accel.append(0)
    else: # 10% Chutes
        X_accel.append([np.random.normal(15, 5), np.random.normal(15, 5), np.random.normal(15, 5)])
        y_accel.append(1)

rf_fall = RandomForestClassifier(n_estimators=50, random_state=42)
rf_fall.fit(X_accel, y_accel)
joblib.dump(rf_fall, os.path.join(models_dir, 'rf_fall.pkl'))

print("[3/3] Entraînement du Réseau de Neurones LSTM (Historique Vitaux)...")
# Format LSTM : [samples, timesteps, features] -> Historique de 10 mesures, 2 features (HR, SpO2)
X_vitals = np.random.rand(2000, 10, 2)
y_vitals = np.random.randint(0, 2, 2000) # 0: Normal, 1: Risque Malaise

model_lstm = Sequential()
model_lstm.add(LSTM(16, input_shape=(10, 2), activation='relu'))
model_lstm.add(Dense(1, activation='sigmoid'))
model_lstm.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model_lstm.fit(X_vitals, y_vitals, epochs=5, batch_size=32, verbose=0)
model_lstm.save(os.path.join(models_dir, 'lstm_vitals.keras'))

print("[*] TOUS LES MODÈLES ONT ÉTÉ SAUVEGARDÉS AVEC SUCCÈS !")