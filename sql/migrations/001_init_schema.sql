-- sql/migrations/001_init_schema.sql
-- 初始化資料庫 Schema
-- 支援 PostgreSQL 與 Oracle
-- ============================================

-- ============================================
-- PostgreSQL 版本
-- ============================================

-- 患者表
CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255),
    birth_date DATE,
    gender CHAR(1),
    admission_date TIMESTAMP,
    department VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients(patient_id);

-- 護理紀錄表
CREATE TABLE IF NOT EXISTS nursing_records (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    record_time TIMESTAMP NOT NULL,
    nursing_note TEXT,
    assessment TEXT,
    intervention TEXT,
    response TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nursing_records_patient_id ON nursing_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_nursing_records_time ON nursing_records(record_time);

-- 生理監測表
CREATE TABLE IF NOT EXISTS vital_signs (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    record_time TIMESTAMP NOT NULL,
    temperature NUMERIC(5,2),
    heart_rate NUMERIC(5,0),
    blood_pressure_sys NUMERIC(5,0),
    blood_pressure_dia NUMERIC(5,0),
    respiratory_rate NUMERIC(5,0),
    oxygen_saturation NUMERIC(5,2),
    gcs_score NUMERIC(2,0),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vital_signs_patient_id ON vital_signs(patient_id);
CREATE INDEX IF NOT EXISTS idx_vital_signs_time ON vital_signs(record_time);

-- 檢驗結果表
CREATE TABLE IF NOT EXISTS lab_results (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    test_time TIMESTAMP NOT NULL,
    test_name VARCHAR(255),
    result_value NUMERIC(15,6),
    unit VARCHAR(50),
    reference_range VARCHAR(100),
    abnormal_flag CHAR(1),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lab_results_patient_id ON lab_results(patient_id);
CREATE INDEX IF NOT EXISTS idx_lab_results_time ON lab_results(test_time);

-- 使用者表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 模板表
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) DEFAULT 'general',
    content TEXT,
    created_by VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category);

-- ============================================
-- Oracle 版本（註釋示意）
-- ============================================
/*
-- 患者表
CREATE TABLE patients (
    id NUMBER PRIMARY KEY,
    patient_id VARCHAR2(20) UNIQUE NOT NULL,
    name VARCHAR2(255),
    birth_date DATE,
    gender CHAR(1),
    admission_date TIMESTAMP,
    department VARCHAR2(100)
);

CREATE SEQUENCE patients_id_seq START WITH 1;

-- 護理紀錄表
CREATE TABLE nursing_records (
    id NUMBER PRIMARY KEY,
    patient_id VARCHAR2(20) NOT NULL REFERENCES patients(patient_id),
    record_time TIMESTAMP NOT NULL,
    nursing_note CLOB,
    assessment CLOB,
    intervention CLOB,
    response CLOB
);

CREATE SEQUENCE nursing_records_id_seq START WITH 1;

-- 生理監測表
CREATE TABLE vital_signs (
    id NUMBER PRIMARY KEY,
    patient_id VARCHAR2(20) NOT NULL REFERENCES patients(patient_id),
    record_time TIMESTAMP NOT NULL,
    temperature NUMBER(5,2),
    heart_rate NUMBER(5),
    blood_pressure_sys NUMBER(5),
    blood_pressure_dia NUMBER(5),
    respiratory_rate NUMBER(5),
    oxygen_saturation NUMBER(5,2),
    gcs_score NUMBER(2)
);

CREATE SEQUENCE vital_signs_id_seq START WITH 1;

-- 檢驗結果表
CREATE TABLE lab_results (
    id NUMBER PRIMARY KEY,
    patient_id VARCHAR2(20) NOT NULL REFERENCES patients(patient_id),
    test_time TIMESTAMP NOT NULL,
    test_name VARCHAR2(255),
    result_value NUMBER(15,6),
    unit VARCHAR2(50),
    reference_range VARCHAR2(100),
    abnormal_flag CHAR(1)
);

CREATE SEQUENCE lab_results_id_seq START WITH 1;
*/
