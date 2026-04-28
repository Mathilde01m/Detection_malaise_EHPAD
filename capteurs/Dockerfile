# Utilise une image Python légère
FROM python:3.10-slim

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie le fichier des dépendances
COPY requirements.txt .

# Installe les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le contenu du dossier local "capteurs" dans le dossier "/app/capteurs" du conteneur
COPY . /app/capteurs/

# Définit le chemin Python pour que les imports "from capteurs.X" fonctionnent
ENV PYTHONPATH=/app

# Commande par défaut pour lancer ton script
CMD ["python", "-m", "capteurs.main"]