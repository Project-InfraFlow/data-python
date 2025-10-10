CREATE DATABASE IF NOT EXISTS Infraflow;
USE Infraflow;

CREATE TABLE IF NOT EXISTS tipo_usuario (
    id_tipo_usuario INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_tipo_usuario PRIMARY KEY (id_tipo_usuario),
    permissao VARCHAR(45) CONSTRAINT chk_tipo_user CHECK (permissao in ("administrador", "comum")),
    descricao VARCHAR(45)
);

CREATE TABLE IF NOT EXISTS empresa (
    id_empresa INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_empresa PRIMARY KEY (id_empresa),
    razao_social VARCHAR(45),
    cnpj VARCHAR(14),
    status TINYINT,
    fk_tipo_contato INT 
);

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_Usuario PRIMARY KEY (id_usuario),
    nome VARCHAR(45),
    email VARCHAR(45),
    senha VARCHAR(45),
    fk_id_tipo_usuario INT NOT NULL,
    fk_empresa INT NOT NULL,
    CONSTRAINT fk_usuario_tipo_usuario FOREIGN KEY (fk_id_tipo_usuario) REFERENCES tipo_usuario(id_tipo_usuario),
    CONSTRAINT fk_empresa FOREIGN KEY (fk_empresa) REFERENCES empresa(id_empresa)
);

CREATE TABLE IF NOT EXISTS token_acesso (
    id_token_acesso INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_token_acesso PRIMARY KEY (id_token_acesso),
    data_criacao DATETIME,
    data_expiracao DATETIME,
    ativo TINYINT,
    token VARCHAR(6),
    fk_id_empresa INT NOT NULL,
    CONSTRAINT fk_token_acesso_empresa FOREIGN KEY (fk_id_empresa) REFERENCES empresa(id_empresa)
);

CREATE TABLE IF NOT EXISTS tipo_contato (
    id_tipo_contato INT PRIMARY KEY AUTO_INCREMENT,
    telefone VARCHAR (20),
    email VARCHAR(255)
);

ALTER TABLE empresa ADD CONSTRAINT fk_tipo_contato FOREIGN KEY (fk_tipo_contato) REFERENCES tipo_contato(id_tipo_contato);

CREATE TABLE IF NOT EXISTS maquina (
    id_maquina INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_maquina PRIMARY KEY (id_maquina),
    nome_maquina VARCHAR(45),
    so VARCHAR(45),
    localizacao VARCHAR(45),
    km VARCHAR(45),
    fk_empresa_maquina INT,
    CONSTRAINT fk_empresa_maquina FOREIGN KEY (fk_empresa_maquina) REFERENCES empresa(id_empresa)
);

CREATE TABLE IF NOT EXISTS componente (
    id_componente INT NOT NULL AUTO_INCREMENT,
    fk_id_maquina INT NOT NULL,
    nome_componente VARCHAR(45),
    unidade_de_medida VARCHAR(10),
    CONSTRAINT pk_componente PRIMARY KEY (id_componente),
    CONSTRAINT fk_componente_maquina FOREIGN KEY (fk_id_maquina) REFERENCES maquina(id_maquina)
);

CREATE TABLE IF NOT EXISTS parametro_componente (
    id_parametro_componente INT NOT NULL AUTO_INCREMENT,
    fk_id_componente INT NOT NULL,
    nivel VARCHAR(45),
    min FLOAT,
    max FLOAT,
    CONSTRAINT pk_parametro_componente PRIMARY KEY (id_parametro_componente),
    CONSTRAINT fk_parametro_componente FOREIGN KEY (fk_id_componente) REFERENCES componente(id_componente)
);

CREATE TABLE IF NOT EXISTS nucleo_cpu (
    id_nucleo INT NOT NULL AUTO_INCREMENT,
    fk_id_componente INT NOT NULL,
    fk_id_maquina INT NOT NULL,
    CONSTRAINT pk_nucleo_cpu PRIMARY KEY (id_nucleo),
    CONSTRAINT fk_nucleo_cpu_componente FOREIGN KEY (fk_id_componente) REFERENCES componente(id_componente),
    CONSTRAINT fk_nucleo_cpu_maquina FOREIGN KEY (fk_id_maquina) REFERENCES maquina(id_maquina)
);

CREATE TABLE IF NOT EXISTS leitura (
    id_leitura INT NOT NULL AUTO_INCREMENT,
    fk_id_componente INT NOT NULL,
    fk_id_maquina INT NOT NULL,
    dados_float FLOAT,
    dados_texto VARCHAR (100),
    data_hora_captura DATETIME,
    id_nucleo INT,
    CONSTRAINT pk_leitura PRIMARY KEY (id_leitura),
    CONSTRAINT fk_leitura_componente FOREIGN KEY (fk_id_componente) REFERENCES componente(id_componente),
    CONSTRAINT fk_leitura_maquina FOREIGN KEY (fk_id_maquina) REFERENCES maquina(id_maquina),
    CONSTRAINT fk_leitura_nucleo FOREIGN KEY (id_nucleo) REFERENCES nucleo_cpu(id_nucleo)
);

CREATE TABLE IF NOT EXISTS parametro_alerta(
    id_parametro_alerta INT PRIMARY KEY AUTO_INCREMENT,
    min FLOAT,
    max FLOAT
);

CREATE TABLE IF NOT EXISTS alerta (
    id_alerta INT NOT NULL AUTO_INCREMENT,
    fk_id_leitura INT NOT NULL,
    fk_id_componente INT NOT NULL,
    fk_parametro_alerta INT NOT NULL,
    descricao VARCHAR(45),
    status_alerta TINYINT,
    CONSTRAINT pk_alerta PRIMARY KEY (id_alerta),
    CONSTRAINT fk_alerta_leitura FOREIGN KEY (fk_id_leitura) REFERENCES leitura(id_leitura),
    CONSTRAINT fk_alerta_componente FOREIGN KEY (fk_id_componente) REFERENCES componente(id_componente),
    CONSTRAINT fk_alerta_parametro FOREIGN KEY (fk_parametro_alerta) REFERENCES parametro_alerta(id_parametro_alerta)
);

INSERT INTO tipo_usuario VALUES
(default, "administrador", "acesso geral"),
(default, "comum", "acesso restrito");

-- ATUALIZADO 07/10, 20:55 NICOLLY

-- =============================================================================================================================================

-- Comentado para guardar

-- Empresa
-- INSERT INTO empresa (token_empresa, razao_social, nome_fantasia, cnpj, telefone)
-- VALUES (123456789, 'EmpresaXPTO', 'XPTO', '01234567891234', '11975321122');

-- Tipos de usuário
-- INSERT INTO tipo_usuario (permissao, descricao)
-- VALUES ('admin', 'Administrador'), ('comum', 'Usuário Padrão');

-- Usuário
-- INSERT INTO usuario (nome, email, senha, fk_id_tipo_usuario, fk_token_empresa)
-- VALUES ('João da Silva', 'joao@xpto.com', '123456', 1, 123456789);
       
-- Select Wiew
/*
SELECT
    DATE_FORMAT(l.data_hora_captura, '%d/%m/%Y %H:%i:%s') AS horario,
    SUM(
        CASE
            WHEN l.fk_id_componente = 1
            THEN ROUND(l.dados / (
                SELECT COUNT(*)
                FROM nucleo_cpu n
                WHERE n.fk_id_maquina = l.fk_id_maquina
                  AND n.fk_token_empresa = l.fk_token_empresa
            ), 2)
        END
    ) AS cpu,
    MAX(
        CASE
            WHEN l.fk_id_componente = 2
            THEN ROUND(l.dados, 2)
        END
    ) AS ram,
    MAX(
        CASE
            WHEN l.fk_id_componente = 3
            THEN ROUND(l.dados, 2)
        END
    ) AS disco
FROM leitura l
WHERE l.fk_id_maquina = 1                
  AND l.fk_token_empresa = 123456789      
GROUP BY l.data_hora_captura
ORDER BY l.data_hora_captura DESC
LIMIT 10;
*/








# insert



USE Infraflow;

-- =========================================
-- 1) Pré-requisitos: tipo_contato e empresa
-- =========================================
-- Cria um contato simples para a empresa
INSERT INTO tipo_contato (telefone, email)
VALUES ('11999999999', 'contato@xpto.com');
SET @id_tipo_contato := LAST_INSERT_ID();

-- Cria a empresa com o ID específico solicitado (123456789)
-- Observação: id_empresa é AUTO_INCREMENT, mas o MySQL permite inserir ID manualmente.
INSERT INTO empresa (id_empresa, razao_social, cnpj, status, fk_tipo_contato)
VALUES (123456789, 'Empresa XPTO Ltda', '01234567891234', 1, @id_tipo_contato);

-- Opcional: gera um token de acesso de 6 caracteres para a empresa
INSERT INTO token_acesso (data_criacao, data_expiracao, ativo, token, fk_id_empresa)
VALUES (NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY), 1, 'AB12CD', 123456789);

-- =========================================
-- 2) Usuário (cliente)
-- =========================================
-- Considerando que você já inseriu em tipo_usuario:
-- (1 = administrador, 2 = comum)
-- Inserimos como usuário "comum". Se quiser admin, troque fk_id_tipo_usuario para 1.
INSERT INTO usuario (id_usuario, nome, email, senha, fk_id_tipo_usuario, fk_empresa)
VALUES (1, 'João da Silva', 'joao@xpto.com', '123456', 2, 123456789);

-- =========================================
-- 3) Máquina para a empresa
-- =========================================
INSERT INTO maquina (nome_maquina, so, localizacao, km, fk_empresa_maquina)
VALUES ('srv-xpto-01', 'Ubuntu 22.04', 'Data Center - Rack A3', 'N/A', 123456789);
SET @id_maquina := LAST_INSERT_ID();

-- =========================================
-- 4) Componentes padrão da máquina
--    (CPU, RAM, Disco, Rede)
-- =========================================
-- CPU (%)
INSERT INTO componente (fk_id_maquina, nome_componente, unidade_de_medida)
VALUES (@id_maquina, 'CPU', '%');
SET @id_cpu := LAST_INSERT_ID();

-- RAM (%)
INSERT INTO componente (fk_id_maquina, nome_componente, unidade_de_medida)
VALUES (@id_maquina, 'RAM', '%');
SET @id_ram := LAST_INSERT_ID();

-- Disco (% de uso)
INSERT INTO componente (fk_id_maquina, nome_componente, unidade_de_medida)
VALUES (@id_maquina, 'Disco', '%');
SET @id_disco := LAST_INSERT_ID();

-- Rede (Mbps)
INSERT INTO componente (fk_id_maquina, nome_componente, unidade_de_medida)
VALUES (@id_maquina, 'Rede', 'Mbps');
SET @id_rede := LAST_INSERT_ID();

-- =========================================
-- 5) Parâmetros básicos de alerta por componente
--    (faixas operacionais padrão; ajuste como preferir)
-- =========================================
-- CPU: 0–85% ok
INSERT INTO parametro_componente (fk_id_componente, nivel, min, max)
VALUES (@id_cpu, 'operacional', 0, 85);

-- RAM: 0–90% ok
INSERT INTO parametro_componente (fk_id_componente, nivel, min, max)
VALUES (@id_ram, 'operacional', 0, 90);

-- Disco: 0–85% ok
INSERT INTO parametro_componente (fk_id_componente, nivel, min, max)
VALUES (@id_disco, 'operacional', 0, 85);

-- Rede: até 1000 Mbps (exemplo)
INSERT INTO parametro_componente (fk_id_componente, nivel, min, max)
VALUES (@id_rede, 'operacional', 0, 1000);

-- =========================================
-- 6) Núcleos de CPU (ex.: 4 núcleos)
-- =========================================
INSERT INTO nucleo_cpu (fk_id_componente, fk_id_maquina) VALUES
(@id_cpu, @id_maquina),
(@id_cpu, @id_maquina),
(@id_cpu, @id_maquina),
(@id_cpu, @id_maquina);



SET @host := 'MacBook-85.local';


# maquina

USE Infraflow;

-- Ajuste conforme o seu caso:
SET @id_empresa := 123456789;
SET @host       := 'MacBook-85.local';
SET @so         := 'macOS';
SET @local      := 'N/A';
SET @km         := 'N/A';

-- Insert ÚNICO: Máquina + Componentes (CPU, RAM, Disco)
INSERT INTO maquina (nome_maquina, so, localizacao, km, fk_empresa_maquina)
VALUES (@host, @so, @local, @km, @id_empresa);

-- Recupera ID da máquina recém-criada
SET @id_maquina := LAST_INSERT_ID();

INSERT INTO componente (fk_id_maquina, nome_componente, unidade_de_medida)
VALUES
(@id_maquina, 'CPU', '%'),
(@id_maquina, 'RAM', '%'),
(@id_maquina, 'Disco', '%');

-- Verificação opcional
SELECT @id_maquina AS id_maquina_criada;
SELECT * FROM componente WHERE fk_id_maquina = @id_maquina;

SELECT 
    l.id_leitura,
    m.nome_maquina,
    c.nome_componente,
    l.dados_float,
    l.data_hora_captura,
    l.id_nucleo
FROM leitura l
JOIN componente c ON l.fk_id_componente = c.id_componente
JOIN maquina m ON l.fk_id_maquina = m.id_maquina
ORDER BY l.data_hora_captura DESC
LIMIT 50;



