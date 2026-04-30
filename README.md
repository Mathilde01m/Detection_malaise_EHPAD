# SANTÉ OS — Système de Détection de Malaise en EHPAD

Plateforme temps réel de surveillance des résidents d'EHPAD : constantes vitales, détection de chutes, errance, inactivité prolongée, avec alertes graduées et rapports médicaux générés par IA (Mistral via Ollama).

---

## Architecture globale

```
┌─────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE                       │
│                                                             │
│  [simulateur-vitaux]  →  MQTT  →  [backend-ia]             │
│  [simulateur-capteurs]           ↓          ↓              │
│                              [redis]    [ollama/Mistral]    │
│                                  ↓                         │
│  [frontend / nginx] ←── [fastapi] ←── [postgres]           │
└─────────────────────────────────────────────────────────────┘
```

### Services Docker

| Service | Container | Rôle | Port |
|---|---|---|---|
| `mqtt-broker` | `mqtt_broker` | Bus de messages MQTT (Mosquitto) | 1883 / 9001 (WS) |
| `frontend` | `ehpad_dashboard` | Interface web (Nginx) | 8080 |
| `fastapi` | `ehpad_api` | API REST + authentification JWT | 8000 |
| `postgres` | `ehpad_postgres` | Base de données relationnelle | 5432 |
| `redis-cache` | `redis_cache` | Cache état temps réel des résidents | 6379 |
| `backend-ia` | `backend_ia` | Moteur IA : détection, alertes, LLM | — |
| `ollama` | `ollama_llm` | LLM local Mistral (rapports médicaux) | 11434 |
| `simulateur-vitaux` | `ehpad_simulator_vitaux` | Simulation constantes vitales MQTT | — |
| `simulateur-capteurs` | `ehpad_simulator_capteurs` | Simulation capteurs environnementaux | — |

---

## Flux de données

```
simulateur-vitaux  →  ehpad/residents/{id}/vitals      →  backend-ia → redis
simulateur-capteurs →  ehpad/residents/{id}/environment →  backend-ia → redis
                                                            ↓
                                                    Analyse + graduation
                                                            ↓
                                                   ehpad/alerts  →  frontend
```

- **Vitaux** : fréquence cardiaque, SpO2, température, tension
- **Environnement** : chute détectée, type de chute, localisation, errance, inactivité, niveau d'alerte
- **Alertes** : publiées sur `ehpad/alerts` avec niveau 1→5, texte, rapport LLM si niveau ≥ 4

---

## Niveaux d'alerte

| Niveau | Label | Déclencheur |
|---|---|---|
| 1 | INFORMATION | Immobilité prolongée |
| 2 | ATTENTION | Errance / début d'anomalie vitale |
| 3 | ALERTE | Dégradation persistante des constantes |
| 4 | URGENCE | Constantes fortement dégradées |
| 5 | DANGER VITAL | Chute détectée / constantes critiques persistantes |

Les niveaux ≥ 4 déclenchent un **rapport de transmission infirmière** généré par Mistral.

---

## Backend IA (`backend_IA/`)

### `processor.py`
- Souscrit aux topics MQTT `ehpad/residents/#` et `ehpad/alerts/ack`
- Calcule l'état de chaque résident via :
  - `classify_vitals(hr, spo2)` : stable / moderate / high / critical
  - `classify_fall_from_context(...)` : mechanical / parkinson_balance / cardiac_malaise / syncope_hypotension / malaise
  - `evaluate_resident_state(res_id)` : graduation temporelle des alertes vitales
- Publie les alertes sur `ehpad/alerts`
- Gère les ACK soignants (suppression 3 min)

### `models/ai_engine.py`
Trois modèles ML (mode dégradé par seuils si non entraînés) :
- **Isolation Forest** (`iso_ambient.pkl`) : anomalie environnementale
- **Random Forest** (`rf_fall.pkl`) : détection de chute accélérométrique
- **LSTM** (`lstm_vitals.keras`) : prédiction de risque vital sur séquence de 10 mesures

---

## API REST (`api/`)

### Authentification JWT

Toutes les routes (sauf `/login`) nécessitent un header :
```
Authorization: Bearer <token>
```

### Endpoints

| Méthode | Route | Rôle | Accès |
|---|---|---|---|
| `GET` | `/health` | Vérification API | Public |
| `POST` | `/login` | Connexion → token JWT | Public |
| `GET` | `/me` | Infos utilisateur connecté | Tous |
| `GET` | `/residents` | Liste tous les résidents avec constantes | Staff uniquement |
| `GET` | `/my-resident` | Résident lié au compte famille | Famille uniquement |

### Réponse `/login`
```json
{
  "token": "<jwt>",
  "role": "nurse",
  "name": "Claire Durand",
  "email": "claire.durand@ehpad.local"
}
```

---

## Base de données (`database/`)

### Tables principales

| Table | Contenu |
|---|---|
| `residents` | Données fixes (âge, pathologie, mobilité) |
| `resident_rooms` | Chambre, zone, étage |
| `baseline_vitals` | Constantes de référence |
| `vital_measurements` | Mesures temps réel |
| `movement_events` | Chutes, déplacements, inactivité |
| `alerts` | Alertes graduées 1→5 |
| `users` | Comptes (staff + famille) |
| `family_access` | Lien famille ↔ résident |
| `risk_predictions` | Résultats IA |

### Vues utiles
```sql
SELECT * FROM dashboard_global_view;
SELECT * FROM active_alerts_dashboard;
```

---

## Frontend (`frontend/`)

Interface web temps réel (HTML/CSS/JS vanilla) servie par Nginx.

### Vues

**Vue soignant** (rôle : `admin`, `doctor`, `nurse`, `caregiver`)
- Grille de toutes les chambres avec constantes vitales en temps réel
- Badge événement par carte : 🔴 CHUTE / 🟠 ERRANCE / 🟡 INACTIVITÉ
- Badge IA niveau 1→5 avec texte d'alerte
- Panneau patient détaillé : historique, rapport LLM Mistral
- Carte de l'unité avec statut par chambre
- Validation d'intervention (ACK) qui supprime l'alerte 3 min

**Vue famille** (rôle : `family`)
- Plein écran dédié, totalement séparé du shell soignant
- Affiche uniquement le proche lié au compte
- Constantes vitales en temps réel via MQTT WebSocket
- Statut simplifié (STABLE / URGENT / CRITIQUE)

### MQTT WebSocket
- Hôte : `window.location.hostname`, port `9001`
- Topics écoutés : `ehpad/residents/+/vitals`, `ehpad/residents/+/environment`, `ehpad/alerts`

---

## Comptes de démonstration

Mot de passe universel : **`Demo1234!`**

| Rôle | Exemple d'email |
|---|---|
| Médecin | `medecin@ehpad.local` |
| Infirmière | `claire.durand@ehpad.local` |
| Famille | `famille.martin@ehpad.local` |

> Les 40 comptes famille ont tous le même mot de passe demo stocké sous `hashed_password_demo` en base.

---

## Lancement

```bash
# Démarrer tous les services
docker compose up -d

# Reconstruire l'API (après modification)
docker compose up --build fastapi -d
docker restart ehpad_dashboard

# Accéder à l'interface
open http://localhost:8080
```

### Reset complet de la base
```bash
docker compose down -v
docker compose up -d
```

### Connexion PostgreSQL
```bash
docker exec -it ehpad_postgres psql -U ehpad_user -d ehpad_db
```

### Logs en temps réel
```bash
docker logs -f backend_ia
docker logs -f ehpad_api
```

---

## Règles d'accès par rôle

| Rôle | `/residents` | `/my-resident` | Vue dashboard |
|---|---|---|---|
| `admin` | ✅ | ❌ | Vue soignant complète |
| `doctor` | ✅ | ❌ | Vue soignant complète |
| `nurse` | ✅ | ❌ | Vue soignant complète |
| `caregiver` | ✅ | ❌ | Vue soignant complète |
| `family` | ❌ | ✅ | Vue famille (1 résident) |

---

## Structure du projet

```
Detection_malaise_EHPAD/
├── api/                    # FastAPI — authentification + endpoints REST
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── requirements.txt
│   └── Dockerfile
├── backend_IA/             # Moteur IA — MQTT, alertes, LLM
│   ├── processor.py
│   ├── train_all_models.py
│   ├── models/
│   │   └── ai_engine.py
│   ├── requirements.txt
│   └── Dockerfile
├── simulateur/             # Simulation constantes vitales
│   ├── main.py
│   ├── vitals_generator.py
│   ├── scenario.py
│   └── Dockerfile
├── capteurs/               # Simulation capteurs environnementaux
│   ├── main.py
│   ├── sensor_generator.py
│   └── Dockerfile
├── frontend/               # Interface web
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   └── nginx.conf
├── database/               # Scripts SQL d'initialisation
│   ├── 01_schema.sql
│   ├── 02_import_csv.sql
│   ├── 03_seed_users.sql
│   ├── 04_views.sql
│   └── 05_queries_examples.sql
├── data/                   # Données CSV résidents
├── config/                 # Configuration Mosquitto
│   └── mosquitto.conf
└── docker-compose.yaml
```
