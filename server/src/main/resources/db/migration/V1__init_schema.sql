CREATE DATABASE IF NOT EXISTS TradeAnalytics;
USE TradeAnalytics;
CREATE TABLE location_kind (
                               id TINYINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                               code VARCHAR(20) NOT NULL UNIQUE
);

INSERT INTO location_kind (code) VALUES
                                     ('COUNTRY_HUB'),
                                     ('AIRPORT'),
                                     ('PORT'),
                                     ('CITY');

CREATE TABLE transport_type (
                                id TINYINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                                code VARCHAR(10) NOT NULL UNIQUE
);

INSERT INTO transport_type (code) VALUES
                                      ('AIR'),
                                      ('SEA'),
                                      ('LAND');

CREATE TABLE tariff_type (
                             id TINYINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                             code VARCHAR(20) NOT NULL UNIQUE
);

INSERT INTO tariff_type (code) VALUES
                                   ('MFN'),
                                   ('APPLIED'),
                                   ('AVERAGE'),
                                   ('MOCK');

CREATE TABLE country (
                         id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                         name VARCHAR(100) NOT NULL,
                         iso2 CHAR(2) NOT NULL UNIQUE,
                         iso3 CHAR(3) UNIQUE
);

CREATE TABLE location (
                          id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                          country_id BIGINT UNSIGNED NOT NULL,
                          kind_id TINYINT UNSIGNED NOT NULL,
                          name VARCHAR(100) NOT NULL,
                          code VARCHAR(20),
                          latitude DECIMAL(9,6) NOT NULL,
                          longitude DECIMAL(9,6) NOT NULL,
                          active BOOLEAN NOT NULL DEFAULT TRUE,
                          CONSTRAINT fk_location_country
                              FOREIGN KEY (country_id) REFERENCES country(id),
                          CONSTRAINT fk_location_kind
                              FOREIGN KEY (kind_id) REFERENCES location_kind(id),
                          UNIQUE (country_id, kind_id, code)
);

CREATE TABLE route_edge (
                            id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                            origin_location_id BIGINT UNSIGNED NOT NULL,
                            destination_location_id BIGINT UNSIGNED NOT NULL,
                            transport_type_id TINYINT UNSIGNED NOT NULL,
                            distance_km DECIMAL(10,2) NOT NULL,
                            base_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
                            estimated_hours DECIMAL(10,2),
                            active BOOLEAN NOT NULL DEFAULT TRUE,
                            CONSTRAINT fk_route_origin
                                FOREIGN KEY (origin_location_id) REFERENCES location(id),
                            CONSTRAINT fk_route_destination
                                FOREIGN KEY (destination_location_id) REFERENCES location(id),
                            CONSTRAINT fk_route_transport
                                FOREIGN KEY (transport_type_id) REFERENCES transport_type(id),
                            UNIQUE (origin_location_id, destination_location_id, transport_type_id)
);

CREATE TABLE tariff (
                        id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                        country_id BIGINT UNSIGNED NOT NULL,
                        partner_country_id BIGINT UNSIGNED,
                        hs6_code VARCHAR(6),
                        rate_pct DECIMAL(6,3) NOT NULL,
                        tariff_type_id TINYINT UNSIGNED NOT NULL,
                        source VARCHAR(100),
                        effective_from DATE,
                        effective_to DATE,
                        CONSTRAINT fk_tariff_country
                            FOREIGN KEY (country_id) REFERENCES country(id),
                        CONSTRAINT fk_tariff_partner_country
                            FOREIGN KEY (partner_country_id) REFERENCES country(id),
                        CONSTRAINT fk_tariff_type
                            FOREIGN KEY (tariff_type_id) REFERENCES tariff_type(id)
);