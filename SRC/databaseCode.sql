CREATE DATABASE rainTrack;
USE rainTrack;

CREATE TABLE users (
	id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    cpf VARCHAR(11) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role TINYINT(1) NOT NULL,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);

CREATE TABLE stations (
	id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    latitude VARCHAR(255) NOT NULL,
    longitude VARCHAR(255) NOT NULL,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uuid VARCHAR(17) NOT NULL UNIQUE
);

CREATE TABLE typeParameters (
	id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    typeJson VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL UNIQUE,
    unit VARCHAR(255) NOT NULL,
    numberOfDecimalPlaces INT NOT NULL
);

CREATE TABLE parameters (
	id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    cdTypeParameter INT NOT NULL,
    cdStation INT,
    FOREIGN KEY (cdTypeParameter) REFERENCES typeParameters(id),
    FOREIGN KEY (cdStation) REFERENCES stations(id)
);  

CREATE TABLE measures (
	id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    value FLOAT NOT NULL,
    cdParameter INT NOT NULL,
    measureTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cdParameter) REFERENCES parameters(id)
);

INSERT INTO users (name, cpf, email, password, role) 
VALUES
('Admin', '00000000000', 'raintrack@gmail.com', '123', 1);

-- ===============================
-- TIPOS DE PARÂMETROS
-- ===============================
INSERT INTO typeParameters (typeJson, name, unit, numberOfDecimalPlaces)
VALUES
('temperature', 'Temperatura', '°C', 1),
('humidity', 'Umidade', '%', 0);

-- ===============================
-- ESTAÇÃO METEOROLÓGICA
-- ===============================
INSERT INTO stations (name, latitude, longitude, uuid)
VALUES
('Estação São José dos Campos', '-23.2237', '-45.9009', 'STATION-001');

-- ===============================
-- VÍNCULO DOS PARÂMETROS COM A ESTAÇÃO
-- ===============================
INSERT INTO parameters (cdTypeParameter, cdStation)
VALUES
(
  (SELECT id FROM typeParameters WHERE name = 'Temperatura'),
  (SELECT id FROM stations WHERE uuid = 'STATION-001')
),
(
  (SELECT id FROM typeParameters WHERE name = 'Umidade'),
  (SELECT id FROM stations WHERE uuid = 'STATION-001')
);

-- ===============================
-- MEDIÇÕES FICTÍCIAS - TEMPERATURA
-- ===============================
INSERT INTO measures (value, cdParameter, measureTime)
VALUES
(23.5, (SELECT p.id FROM parameters p 
        JOIN typeParameters t ON p.cdTypeParameter = t.id 
        WHERE t.name = 'Temperatura'), NOW() - INTERVAL 60 MINUTE),

(24.0, (SELECT p.id FROM parameters p 
        JOIN typeParameters t ON p.cdTypeParameter = t.id 
        WHERE t.name = 'Temperatura'), NOW() - INTERVAL 45 MINUTE),

(24.3, (SELECT p.id FROM parameters p 
        JOIN typeParameters t ON p.cdTypeParameter = t.id 
        WHERE t.name = 'Temperatura'), NOW() - INTERVAL 30 MINUTE),

(24.1, (SELECT p.id FROM parameters p 
        JOIN typeParameters t ON p.cdTypeParameter = t.id 
        WHERE t.name = 'Temperatura'), NOW() - INTERVAL 15 MINUTE);

-- ===============================
-- MEDIÇÕES FICTÍCIAS - UMIDADE
-- ===============================
INSERT INTO measures (value, cdParameter, measureTime)
VALUES
(68, (SELECT p.id FROM parameters p 
      JOIN typeParameters t ON p.cdTypeParameter = t.id 
      WHERE t.name = 'Umidade'), NOW() - INTERVAL 60 MINUTE),

(70, (SELECT p.id FROM parameters p 
      JOIN typeParameters t ON p.cdTypeParameter = t.id 
      WHERE t.name = 'Umidade'), NOW() - INTERVAL 45 MINUTE),

(72, (SELECT p.id FROM parameters p 
      JOIN typeParameters t ON p.cdTypeParameter = t.id 
      WHERE t.name = 'Umidade'), NOW() - INTERVAL 30 MINUTE),

(69, (SELECT p.id FROM parameters p 
      JOIN typeParameters t ON p.cdTypeParameter = t.id 
      WHERE t.name = 'Umidade'), NOW() - INTERVAL 15 MINUTE);
