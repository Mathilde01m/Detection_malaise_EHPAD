-- 02_import_csv.sql
-- Import des CSV résidents et chambres.
-- Les fichiers doivent être montés dans /data via docker-compose.
-- =========================================================

CREATE TEMP TABLE tmp_residents_csv (
    resident_id VARCHAR(10),
    age INT,
    pathologie VARCHAR(255),
    mobilite VARCHAR(100),
    risque_principal VARCHAR(255),
    frequence_cardiaque_bpm INT,
    spo2_percent INT,
    tension_arterielle VARCHAR(20),
    temperature_c FLOAT,
    glycemie_mg_dl INT
);

COPY tmp_residents_csv (
    resident_id,
    age,
    pathologie,
    mobilite,
    risque_principal,
    frequence_cardiaque_bpm,
    spo2_percent,
    tension_arterielle,
    temperature_c,
    glycemie_mg_dl
)
FROM '/data/residents.csv'
DELIMITER ','
CSV HEADER;

INSERT INTO residents (
    resident_id,
    age,
    pathologie,
    mobilite,
    risque_principal
)
SELECT
    resident_id,
    age,
    pathologie,
    mobilite,
    risque_principal
FROM tmp_residents_csv;

INSERT INTO baseline_vitals (
    resident_id,
    heart_rate,
    spo2,
    systolic_bp,
    diastolic_bp,
    temperature,
    glucose
)
SELECT
    resident_id,
    frequence_cardiaque_bpm,
    spo2_percent,
    split_part(tension_arterielle, '/', 1)::INT,
    split_part(tension_arterielle, '/', 2)::INT,
    temperature_c,
    glycemie_mg_dl
FROM tmp_residents_csv;

COPY resident_rooms (
    resident_id,
    room,
    zone,
    floor
)
FROM '/data/rooms_mapping.csv'
DELIMITER ','
CSV HEADER;

INSERT INTO patient_state_current (
    resident_id,
    heart_rate,
    spo2,
    temperature,
    glucose,
    room,
    zone,
    floor,
    current_alert_level,
    current_event_type,
    ai_risk_score
)
SELECT
    r.resident_id,
    b.heart_rate,
    b.spo2,
    b.temperature,
    b.glucose,
    rr.room,
    rr.zone,
    rr.floor,
    0,
    'initial_state',
    0
FROM residents r
LEFT JOIN baseline_vitals b ON b.resident_id = r.resident_id
LEFT JOIN resident_rooms rr ON rr.resident_id = r.resident_id;
