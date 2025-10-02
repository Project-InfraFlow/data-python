CREATE DATABASE IF NOT EXISTS Infraflow;
USE Infraflow;

CREATE TABLE IF NOT EXISTS tipo_usuario (
    id_tipo_usuario INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_tipo_usuario PRIMARY KEY (id_tipo_usuario),
    permissao VARCHAR(45),
    descricao VARCHAR(45)
);

CREATE TABLE IF NOT EXISTS empresa (
    id_empresa INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_empresa PRIMARY KEY (id_empresa),
    token_empresa INT,
    razao_social VARCHAR(45),
    nome_fantasia VARCHAR(45),
    cnpj VARCHAR(14),
    telefone VARCHAR(11),
    CONSTRAINT uq_token_empresa UNIQUE (token_empresa)
);

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_Usuario PRIMARY KEY (id_usuario),
    nome VARCHAR(45),
    email VARCHAR(45),
    senha VARCHAR(45),
    fk_id_tipo_usuario INT NOT NULL,
    fk_token_empresa INT NOT NULL, 
    CONSTRAINT fk_usuario_tipo_usuario FOREIGN KEY (fk_id_tipo_usuario) REFERENCES tipo_usuario(id_tipo_usuario),
    CONSTRAINT fk_usuario_empresa FOREIGN KEY (fk_token_empresa) REFERENCES empresa(token_empresa)
);

CREATE TABLE IF NOT EXISTS token_acesso (
    id_token_acesso INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_token_acesso PRIMARY KEY (id_token_acesso),
    data_criacao DATETIME,
    data_expiracao DATETIME,
    ativo TINYINT,
    token VARCHAR(45),
    fk_id_usuario INT NOT NULL,
    fk_id_tipo_usuario INT,
    CONSTRAINT fk_token_acesso_usuario FOREIGN KEY (fk_id_usuario) REFERENCES usuario(id_usuario),
    CONSTRAINT fk_token_acesso_tipo_usuario FOREIGN KEY (fk_id_tipo_usuario) REFERENCES tipo_usuario(id_tipo_usuario)
);

CREATE TABLE IF NOT EXISTS maquina (
    id_maquina INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_maquina PRIMARY KEY (id_maquina),
    fk_token_empresa INT NOT NULL,
    nome_maquina VARCHAR(45),
    so VARCHAR(45),
    localizacao VARCHAR(45),
    km VARCHAR(45),
    CONSTRAINT fk_maquina_empresa FOREIGN KEY (fk_token_empresa) REFERENCES empresa(token_empresa)
);

CREATE TABLE IF NOT EXISTS componente (
    id_componente INT NOT NULL,
    fk_id_maquina INT NOT NULL,
    CONSTRAINT pk_componente PRIMARY KEY (id_componente, fk_id_maquina),
    fk_token_empresa INT NOT NULL, 
    nome_componente VARCHAR(45),
    unidade_de_medida VARCHAR(10),
    CONSTRAINT fk_componente_maquina FOREIGN KEY (fk_id_maquina) REFERENCES maquina(id_maquina),
    CONSTRAINT fk_componente_empresa FOREIGN KEY (fk_token_empresa) REFERENCES empresa(token_empresa)
);

CREATE TABLE IF NOT EXISTS nucleo_cpu (
    id_nucleo INT NOT NULL,
    fk_id_componente INT NOT NULL,
    fk_id_maquina INT NOT NULL,
    CONSTRAINT pk_nucleo_cpu PRIMARY KEY (id_nucleo, fk_id_componente, fk_id_maquina),
    fk_token_empresa INT NOT NULL, 
    CONSTRAINT fk_nucleo_cpu_componente FOREIGN KEY (fk_id_componente, fk_id_maquina) REFERENCES componente(id_componente, fk_id_maquina),
    CONSTRAINT fk_nucleo_cpu_empresa FOREIGN KEY (fk_token_empresa) REFERENCES empresa(token_empresa)
);

CREATE TABLE IF NOT EXISTS parametro_componente (
    id_parametro_componente INT NOT NULL,
    fk_id_componente INT NOT NULL,
    fk_id_maquina INT NOT NULL,
    CONSTRAINT pk_parametro_componente PRIMARY KEY (id_parametro_componente, fk_id_componente, fk_id_maquina),
    fk_token_empresa INT NOT NULL,
    nivel VARCHAR(45),
    min FLOAT,
    max FLOAT,
    CONSTRAINT fk_parametro_componente FOREIGN KEY (fk_id_componente, fk_id_maquina) REFERENCES componente(id_componente, fk_id_maquina),
    CONSTRAINT fk_parametro_componente_empresa FOREIGN KEY (fk_token_empresa) REFERENCES empresa(token_empresa)
);

CREATE TABLE IF NOT EXISTS leitura (
    id_leitura INT NOT NULL AUTO_INCREMENT,
        CONSTRAINT pk_leitura PRIMARY KEY (id_leitura),
    fk_id_componente INT NOT NULL,
    fk_id_maquina INT NOT NULL,
    fk_token_empresa INT NOT NULL, 
    dados FLOAT,
    data_hora_captura DATETIME,
    id_nucleo INT,
    CONSTRAINT fk_leitura_componente FOREIGN KEY (fk_id_componente, fk_id_maquina) REFERENCES componente(id_componente, fk_id_maquina),
    CONSTRAINT fk_leitura_nucleo_cpu FOREIGN KEY (id_nucleo, fk_id_componente, fk_id_maquina) REFERENCES nucleo_cpu(id_nucleo, fk_id_componente, fk_id_maquina),
    CONSTRAINT fk_leitura_empresa FOREIGN KEY (fk_token_empresa) REFERENCES empresa(token_empresa)
);

CREATE TABLE IF NOT EXISTS alerta (
    id_alerta INT NOT NULL AUTO_INCREMENT,
    CONSTRAINT pk_alerta PRIMARY KEY (id_alerta),
    fk_id_leitura INT,
    fk_id_componente INT NOT NULL,
    fk_id_maquina INT NOT NULL,
    fk_token_empresa INT,
    fk_id_parametro INT,
    fk_id_parametro_maquina INT,
    fk_id_parametro_token_empresa INT,
    descricao VARCHAR(45),
    status_alerta TINYINT,
    CONSTRAINT fk_alerta_leitura FOREIGN KEY (fk_id_leitura) REFERENCES leitura(id_leitura),
    CONSTRAINT fk_alerta_parametro_componente FOREIGN KEY (fk_id_parametro, fk_id_componente, fk_id_maquina)
    REFERENCES parametro_componente(id_parametro_componente, fk_id_componente, fk_id_maquina),
    CONSTRAINT fk_alerta_empresa FOREIGN KEY (fk_token_empresa) REFERENCES empresa(token_empresa)
);

-- Empresa
INSERT INTO empresa (token_empresa, razao_social, nome_fantasia, cnpj, telefone)
VALUES (123456789, 'EmpresaXPTO', 'XPTO', '01234567891234', '11975321122');

-- Tipos de usuário
INSERT INTO tipo_usuario (permissao, descricao)
VALUES ('admin', 'Administrador'), ('comum', 'Usuário Padrão');

-- Usuário
INSERT INTO usuario (nome, email, senha, fk_id_tipo_usuario, fk_token_empresa)
VALUES ('João da Silva', 'joao@xpto.com', '123456', 1, 123456789);
        

-- Select Wiew

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
WHERE l.fk_id_maquina = 1                 -- coloque aqui o ID da máquina que quer consultar
  AND l.fk_token_empresa = 123456789      -- coloque aqui o token da empresa
GROUP BY l.data_hora_captura
ORDER BY l.data_hora_captura DESC
LIMIT 10;

    


    



