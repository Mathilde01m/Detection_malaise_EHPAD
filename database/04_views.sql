-- 04_views.sql
-- Vues utiles pour le dashboard, le backend et les rôles.
-- =========================================================

CREATE OR REPLACE VIEW dashboard_global_view AS
SELECT
    r.resident_id,
    r.age,
    r.pathologie,
    r.mobilite,
    r.risque_principal,
    rr.room,
    rr.zone,
    rr.floor,
    pcs.heart_rate,
    pcs.spo2,
    pcs.temperature,
    pcs.glucose,
    pcs.movement_level,
    pcs.bed_sensor,
    pcs.room_motion,
    pcs.corridor_motion,
    pcs.door_sensor,
    pcs.bathroom_motion,
    pcs.common_area_presence,
    pcs.current_alert_level,
    pcs.current_event_type,
    pcs.ai_risk_score,
    pcs.updated_at
FROM residents r
LEFT JOIN resident_rooms rr ON rr.resident_id = r.resident_id
LEFT JOIN patient_state_current pcs ON pcs.resident_id = r.resident_id;

CREATE OR REPLACE VIEW active_alerts_view AS
SELECT
    a.id,
    a.resident_id,
    rr.room,
    rr.zone,
    rr.floor,
    a.alert_level,
    a.title,
    a.message,
    a.status,
    a.source,
    a.created_at
FROM alerts a
LEFT JOIN resident_rooms rr ON rr.resident_id = a.resident_id
WHERE a.status = 'active'
ORDER BY a.alert_level DESC, a.created_at DESC;

CREATE OR REPLACE VIEW family_access_view AS
SELECT
    u.id AS user_id,
    u.firstname,
    u.lastname,
    u.email,
    fa.resident_id,
    fa.relationship,
    rr.room,
    rr.zone,
    rr.floor
FROM users u
JOIN family_access fa ON fa.user_id = u.id
LEFT JOIN resident_rooms rr ON rr.resident_id = fa.resident_id
WHERE u.role = 'family';

CREATE OR REPLACE VIEW professional_users_view AS
SELECT
    id,
    firstname,
    lastname,
    email,
    role,
    phone,
    is_active
FROM users
WHERE role IN ('admin', 'doctor', 'nurse', 'caregiver')
ORDER BY role, lastname, firstname;

CREATE OR REPLACE VIEW latest_vitals_view AS
SELECT DISTINCT ON (resident_id)
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
    measured_at
FROM vital_measurements
ORDER BY resident_id, measured_at DESC;

CREATE OR REPLACE VIEW latest_environment_view AS
SELECT DISTINCT ON (resident_id)
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
    measured_at
FROM environment_measurements
ORDER BY resident_id, measured_at DESC;
