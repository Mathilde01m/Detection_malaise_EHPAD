-- =========================================================
-- 05_queries_examples.sql
-- Requêtes de test utiles après docker compose up.
-- =========================================================

-- Toutes les tables
\dt

-- Compteurs principaux
SELECT COUNT(*) AS residents_count FROM residents;
SELECT COUNT(*) AS rooms_count FROM resident_rooms;
SELECT COUNT(*) AS users_count FROM users;
SELECT COUNT(*) AS family_access_count FROM family_access;

-- Dashboard global
SELECT * FROM dashboard_global_view ORDER BY room LIMIT 10;

-- Accès famille : ce que voit un compte family précis
SELECT
    p.*
FROM residents p
JOIN family_access fa ON fa.resident_id = p.resident_id
JOIN users u ON u.id = fa.user_id
WHERE u.email = 'camille.martin@mail.local';

-- Tous les patients visibles par un professionnel
SELECT * FROM dashboard_global_view ORDER BY room;

-- Insertion exemple : payload vital issu du simulateur
INSERT INTO vital_measurements (
    resident_id,
    heart_rate,
    spo2,
    systolic_bp,
    diastolic_bp,
    temperature,
    glucose,
    movement_level,
    fall_detected,
    fall_related_to_malaise,
    door_event,
    ai_risk_score,
    predicted_by_ai,
    event_type,
    alert_level,
    raw_payload
)
VALUES (
    'R21',
    122,
    96,
    95,
    60,
    36.8,
    110,
    20,
    false,
    false,
    NULL,
    88,
    true,
    'cardiac_malaise_predicted',
    3,
    '{"source":"manual_test","topic":"ehpad/residents/R21/vitals"}'::jsonb
);

-- Insertion exemple : payload environnement issu des capteurs
INSERT INTO environment_measurements (
    resident_id,
    room,
    zone,
    floor,
    bed_sensor,
    room_motion,
    corridor_motion,
    door_sensor,
    bathroom_motion,
    common_area_presence,
    event_type,
    alert_level,
    raw_payload
)
VALUES (
    'R7',
    '107',
    'Aile A',
    1,
    false,
    false,
    true,
    'main_exit_opened',
    false,
    false,
    'exit_attempt',
    3,
    '{"source":"manual_test","topic":"ehpad/residents/R7/environment"}'::jsonb
);

-- Mise à jour du cache dashboard après réception vitals
UPDATE patient_state_current pcs
SET
    heart_rate = v.heart_rate,
    spo2 = v.spo2,
    temperature = v.temperature,
    glucose = v.glucose,
    movement_level = v.movement_level,
    current_alert_level = GREATEST(COALESCE(pcs.current_alert_level, 0), COALESCE(v.alert_level, 0)),
    current_event_type = v.event_type,
    ai_risk_score = v.ai_risk_score,
    updated_at = CURRENT_TIMESTAMP
FROM latest_vitals_view v
WHERE pcs.resident_id = v.resident_id;

-- Mise à jour du cache dashboard après réception environment
UPDATE patient_state_current pcs
SET
    room = e.room,
    zone = e.zone,
    floor = e.floor,
    bed_sensor = e.bed_sensor,
    room_motion = e.room_motion,
    corridor_motion = e.corridor_motion,
    door_sensor = e.door_sensor,
    bathroom_motion = e.bathroom_motion,
    common_area_presence = e.common_area_presence,
    current_alert_level = GREATEST(COALESCE(pcs.current_alert_level, 0), COALESCE(e.alert_level, 0)),
    current_event_type = e.event_type,
    updated_at = CURRENT_TIMESTAMP
FROM latest_environment_view e
WHERE pcs.resident_id = e.resident_id;

-- Alertes actives
SELECT * FROM active_alerts_view;

-- Derniers vitals
SELECT * FROM latest_vitals_view WHERE resident_id = 'R21';

-- Dernier environnement
SELECT * FROM latest_environment_view WHERE resident_id = 'R7';

