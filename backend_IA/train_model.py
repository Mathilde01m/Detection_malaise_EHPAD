import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os

print("[*] Génération des données d'entraînement synthétiques...")

# On crée une base de données de 5000 historiques de patients (fenêtres de 10 secondes)
data = []
labels = []

for _ in range(5000):
    # 70% de cas normaux (Label 0)
    if np.random.rand() > 0.3:
        hr_base = np.random.randint(60, 95)
        spo2_base = np.random.randint(95, 100)
        # Constantes stables
        hr_values = [hr_base + np.random.randint(-2, 3) for _ in range(10)]
        spo2_values = [spo2_base + np.random.randint(-1, 2) for _ in range(10)]
        label = 0
    # 30% de cas "Pré-Malaise" (Label 3)
    else:
        hr_base = np.random.randint(70, 110)
        spo2_base = np.random.randint(90, 97)
        # Le rythme cardiaque monte, la SpO2 chute
        hr_values = [hr_base + (i * np.random.uniform(1, 3)) for i in range(10)]
        spo2_values = [spo2_base - (i * np.random.uniform(0.5, 1.5)) for i in range(10)]
        label = 3

    # Extraction des "Features" (Caractéristiques) que l'IA va regarder
    hr_mean = np.mean(hr_values)
    spo2_min = np.min(spo2_values)
    hr_trend = np.polyfit(range(10), hr_values, 1)[0] # Tendance (hausse/baisse)
    spo2_trend = np.polyfit(range(10), spo2_values, 1)[0]

    data.append([hr_mean, spo2_min, hr_trend, spo2_trend])
    labels.append(label)

df = pd.DataFrame(data, columns=['hr_mean', 'spo2_min', 'hr_trend', 'spo2_trend'])

print("[*] Entraînement du modèle d'Intelligence Artificielle (Random Forest)...")
X_train, X_test, y_train, y_test = train_test_split(df, labels, test_size=0.2)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print(f"[*] Précision de l'IA : {accuracy * 100:.2f}%")

# Sauvegarde du modèle entraîné
save_dir = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(save_dir, exist_ok=True)
model_path = os.path.join(save_dir, 'trained_model.pkl')

joblib.dump(model, model_path)
print(f"[*] Modèle sauvegardé avec succès dans : {model_path}")