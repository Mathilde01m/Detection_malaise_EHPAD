# Utilise une image Python légère
FROM python:3.10-slim

# Définit le dossier de travail
WORKDIR /app

# Copie le fichier des dépendances
COPY requirements.txt .

# Installe les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le contenu du dossier local "simulateur" dans "/app/simulateur"
COPY . /app/simulateur/

# Indispensable pour les imports
ENV PYTHONPATH=/app

# Commande par défaut pour lancer ton simulateur
CMD ["python", "-m", "simulateur.main"]