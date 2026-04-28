-- =========================================================
-- 01_schema.sql
-- Base de données EHPAD - Résidents, constantes vitales,
-- capteurs environnementaux, alertes, utilisateurs, IA.
-- =========================================================

CREATE TABLE residents (
    resident_id VARCHAR(10) PRIMARY KEY,
    age INT NOT NULL,
    pathologie VARCHAR(255),
    mobilite VARCHAR(100),
    risque_principal VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE resident_rooms (
    id SERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    room VARCHAR(20) NOT NULL,
    zone VARCHAR(100),
    floor INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(resident_id)
);

CREATE TABLE baseline_vitals (
    id SERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    heart_rate INT,
    spo2 INT,
    systolic_bp INT,
    diastolic_bp INT,
    temperature FLOAT,
    glucose INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(resident_id)
);

CREATE TABLE vital_measurements (
    id BIGSERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    heart_rate FLOAT,
    spo2 FLOAT,
    systolic_bp FLOAT,
    diastolic_bp FLOAT,
    temperature FLOAT,
    glucose FLOAT,
    movement_level INT,
    fall_detected BOOLEAN DEFAULT FALSE,
    fall_related_to_malaise BOOLEAN DEFAULT FALSE,
    door_event VARCHAR(100),
    ai_risk_score FLOAT DEFAULT 0,
    predicted_by_ai BOOLEAN DEFAULT FALSE,
    event_type VARCHAR(100) DEFAULT 'normal',
    alert_level INT DEFAULT 0,
    raw_payload JSONB,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE environment_measurements (
    id BIGSERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    room VARCHAR(20),
    zone VARCHAR(100),
    floor INT,
    bed_sensor BOOLEAN,
    room_motion BOOLEAN,
    corridor_motion BOOLEAN,
    door_sensor VARCHAR(100),
    bathroom_motion BOOLEAN,
    common_area_presence BOOLEAN,
    event_type VARCHAR(100) DEFAULT 'environment_normal',
    alert_level INT DEFAULT 0,
    raw_payload JSONB,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE movement_events (
    id BIGSERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    source VARCHAR(50) CHECK (source IN ('vitals', 'environment', 'manual', 'unknown')) DEFAULT 'unknown',
    event_type VARCHAR(100),
    movement_level INT,
    fall_detected BOOLEAN DEFAULT FALSE,
    fall_related_to_malaise BOOLEAN DEFAULT FALSE,
    door_event VARCHAR(100),
    location VARCHAR(100),
    alert_level INT DEFAULT 0,
    raw_payload JSONB,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE malaise_events (
    id BIGSERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    malaise_type VARCHAR(50) CHECK (
        malaise_type IN ('vital_degradation', 'fall_related', 'daily_fall', 'wandering', 'immobility', 'unknown')
    ) DEFAULT 'unknown',
    cause VARCHAR(255),
    severity INT CHECK (severity BETWEEN 1 AND 5),
    source_event_type VARCHAR(100),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    malaise_event_id BIGINT REFERENCES malaise_events(id) ON DELETE SET NULL,
    alert_level INT CHECK (alert_level BETWEEN 1 AND 5),
    title VARCHAR(255),
    message TEXT,
    status VARCHAR(50) CHECK (status IN ('active', 'acknowledged', 'escalated', 'resolved')) DEFAULT 'active',
    source VARCHAR(50) CHECK (source IN ('vitals', 'environment', 'ai', 'manual', 'unknown')) DEFAULT 'unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    firstname VARCHAR(100),
    lastname VARCHAR(100),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) CHECK (role IN ('admin', 'doctor', 'nurse', 'caregiver', 'family')) NOT NULL,
    phone VARCHAR(30),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE family_access (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    relationship VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, resident_id)
);

CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE,
    ip_address VARCHAR(100),
    device_info TEXT,
    login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_at TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(50) CHECK (status IN ('active', 'expired', 'disconnected')) DEFAULT 'active'
);

CREATE TABLE risk_predictions (
    id BIGSERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    risk_score FLOAT,
    prediction_window_minutes INT DEFAULT 30,
    predicted_event VARCHAR(100),
    predicted_by_ai BOOLEAN DEFAULT TRUE,
    features JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE access_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE SET NULL,
    action VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sensor_messages (
    id BIGSERIAL PRIMARY KEY,
    resident_id VARCHAR(10) REFERENCES residents(resident_id) ON DELETE CASCADE,
    sensor_category VARCHAR(50) CHECK (sensor_category IN ('vitals', 'environment', 'unknown')) DEFAULT 'unknown',
    mqtt_topic VARCHAR(255),
    payload JSONB,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE patient_state_current (
    resident_id VARCHAR(10) PRIMARY KEY REFERENCES residents(resident_id) ON DELETE CASCADE,
    heart_rate FLOAT,
    spo2 FLOAT,
    temperature FLOAT,
    glucose FLOAT,
    movement_level INT,
    room VARCHAR(20),
    zone VARCHAR(100),
    floor INT,
    bed_sensor BOOLEAN,
    room_motion BOOLEAN,
    corridor_motion BOOLEAN,
    door_sensor VARCHAR(100),
    bathroom_motion BOOLEAN,
    common_area_presence BOOLEAN,
    current_alert_level INT DEFAULT 0,
    current_event_type VARCHAR(100),
    ai_risk_score FLOAT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_resident_rooms_resident ON resident_rooms(resident_id);
CREATE INDEX idx_baseline_vitals_resident ON baseline_vitals(resident_id);
CREATE INDEX idx_vitals_resident_time ON vital_measurements(resident_id, measured_at DESC);
CREATE INDEX idx_vitals_event_type ON vital_measurements(event_type);
CREATE INDEX idx_vitals_alert_level ON vital_measurements(alert_level);
CREATE INDEX idx_environment_resident_time ON environment_measurements(resident_id, measured_at DESC);
CREATE INDEX idx_environment_event_type ON environment_measurements(event_type);
CREATE INDEX idx_environment_alert_level ON environment_measurements(alert_level);
CREATE INDEX idx_movement_resident_time ON movement_events(resident_id, detected_at DESC);
CREATE INDEX idx_movement_event_type ON movement_events(event_type);
CREATE INDEX idx_malaise_resident_time ON malaise_events(resident_id, started_at DESC);
CREATE INDEX idx_alerts_resident_status ON alerts(resident_id, status);
CREATE INDEX idx_alerts_level ON alerts(alert_level);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_predictions_resident_time ON risk_predictions(resident_id, created_at DESC);
CREATE INDEX idx_sensor_messages_resident_time ON sensor_messages(resident_id, received_at DESC);
CREATE INDEX idx_sensor_messages_category ON sensor_messages(sensor_category);
CREATE INDEX idx_family_access_user ON family_access(user_id);
CREATE INDEX idx_family_access_resident ON family_access(resident_id);
CREATE INDEX idx_sessions_user_status ON user_sessions(user_id, status);
