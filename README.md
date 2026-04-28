# Base de données EHPAD - Projet détection de malaise

## Contenu

```txt
ehpad_database/
├── docker-compose.yml
├── data/
│   ├── residents.csv
│   └── rooms_mapping.csv
└── database/
    ├── 01_schema.sql
    ├── 02_import_csv.sql
    ├── 03_seed_users.sql
    ├── 04_views.sql
    └── 05_queries_examples.sql
```

## Lancement

```bash
docker compose up -d
```

Connexion PostgreSQL :

```bash
docker exec -it ehpad_postgres psql -U ehpad_user -d ehpad_db
```

## Reset complet

Si tu modifies les scripts SQL, PostgreSQL ne les rejoue pas automatiquement si le volume existe déjà.
Pour repartir de zéro :

```bash
docker compose down -v
docker compose up -d
```

## Tables principales

- `residents` : infos fixes des 40 résidents
- `resident_rooms` : chambre, zone, étage
- `baseline_vitals` : constantes de référence issues du CSV
- `patient_state_current` : dernier état pour le dashboard
- `vital_measurements` : mesures temps réel du simulateur
- `movement_events` : chutes, déplacements, inactivité
- `malaise_events` : séparation malaise vital / chute
- `alerts` : alertes graduées niveau 1 à 5
- `users` : familles + professionnels
- `family_access` : limitation d’accès famille à un proche
- `user_sessions` : sessions de connexion
- `sensor_messages` : messages MQTT bruts
- `risk_predictions` : résultats IA
- `access_logs` : traçabilité des accès

## Règle d’accès

- `role IN ('admin', 'doctor', 'nurse', 'caregiver')` : accès à tous les résidents.
- `role = 'family'` : accès uniquement aux résidents liés dans `family_access`.

## Vues utiles

```sql
SELECT * FROM dashboard_residents;
SELECT * FROM active_alerts_dashboard;
```
