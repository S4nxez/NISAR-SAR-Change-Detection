CREATE DATABASE IF NOT EXISTS NisarSar;
USE NisarSar;

CREATE TABLE IF NOT EXISTS sar_site (
                                        id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    country VARCHAR(100) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    change_level VARCHAR(20) NOT NULL,
    change_value VARCHAR(20) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    confidence DECIMAL(4,3) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_sar_site_latitude
    CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_sar_site_longitude
    CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT chk_sar_site_confidence
    CHECK (confidence BETWEEN 0 AND 1)
    );

CREATE TABLE IF NOT EXISTS sar_observation (
                                               id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                                               site_id VARCHAR(50) NOT NULL,
    observation_date VARCHAR(20) NOT NULL,
    vv DECIMAL(7,3) NOT NULL,
    vh DECIMAL(7,3) NOT NULL,
    CONSTRAINT fk_sar_observation_site
    FOREIGN KEY (site_id) REFERENCES sar_site(id)
    ON DELETE CASCADE,
    CONSTRAINT uq_sar_observation_site_date
    UNIQUE (site_id, observation_date)
    );

CREATE INDEX idx_sar_observation_date
    ON sar_observation(observation_date);

CREATE INDEX idx_sar_site_country
    ON sar_site(country);

CREATE INDEX idx_sar_site_change_level
    ON sar_site(change_level);
