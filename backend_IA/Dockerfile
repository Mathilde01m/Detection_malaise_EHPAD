FROM python:3.10-slim

WORKDIR /app

# 1. Installation des dépendances système (souvent requises par scikit-learn et numpy)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 2. Mise à jour de pip (Indispensable pour TensorFlow)
RUN pip install --no-cache-dir --upgrade pip

# 3. Installation de vos librairies Python
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "processor.py"]