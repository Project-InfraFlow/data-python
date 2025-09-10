CREATE DATABASE IF NOT EXISTS Infraflow;
USE Infraflow;

CREATE TABLE IF NOT EXISTS Cliente(
tokenEmpresa INT PRIMARY KEY,
nomeEmpresa VARCHAR(45) NOT NULL,
cnpj VARCHAR(45) NOT NULL,
telefone VARCHAR(45) NOT NULL
);

CREATE TABLE IF NOT EXISTS Usuario(
idUsuario INT AUTO_INCREMENT,
tokenEmpresa INT,
CONSTRAINT pkComposta
	PRIMARY KEY (idUsuario, tokenEmpresa),
nome VARCHAR(45) NOT NULL,
email VARCHAR(45) NOT NULL,
senha VARCHAR(45) NOT NULL,
permisao INT NOT NULL
CONSTRAINT fkUsuarioCliente
	FOREIGN KEY (tokenEmpresa) REFERENCES Cliente(tokenEmpresa)
);

CREATE TABLE IF NOT EXISTS Maquina(
idMaquina INT,
tokenEmpresa INT,
CONSTRAINT pkCompostra
	PRIMARY KEY (idMaquina, tokenEmpresa),
nomeMaquina VARCHAR(45) NOT NULL,
SO VARCHAR(45) NOT NULL,
CONSTRAINT fkMaquinaCliente
	FOREIGN KEY (tokenEmpresa) REFERENCES Cliente(tokenEmpresa)
);

CREATE TABLE IF NOT EXISTS Componente(
idComponente INT,
idMaquina INT,
tokenEmpresa INT,
CONSTRAINT pkCompostra
	PRIMARY KEY (idComponente, idMaquina, tokenEmpresa),
nomeComponente VARCHAR(45) NOT NULL,
UM VARCHAR(10) NOT NULL,
CONSTRAINT fkComponenteMaquina
	FOREIGN KEY (tokenEmpresa) REFERENCES Maquina(tokenEmpresa),
	FOREIGN KEY (idMaquina) REFERENCES Maquina(idMaquina)
);

CREATE TABLE IF NOT EXISTS NucleoCPU(
idNucleoCPU INT AUTO_INCREMENT,
idCPU INT,
idMaquina INT,
tokenEmpresa INT,
CONSTRAINT pkCompostra
	PRIMARY KEY (idNucleoCPU, idCPU, idMaquina, tokenEmpresa),
CONSTRAINT fkNucleoCPUComponente
	FOREIGN KEY (IdCPU) REFERENCES Componente(idComponente),
	FOREIGN KEY (tokenEmpresa) REFERENCES Componente(tokenEmpresa),
	FOREIGN KEY (idMaquina) REFERENCES Componente(idMaquina)
);

CREATE TABLE IF NOT EXISTS Leitura(
idLeitura INT AUTO_INCREMENT,
idComponente INT,
idMaquina INT,
tokenEmpresa INT,
CONSTRAINT pkCompostra
	PRIMARY KEY (idLeitura, idComponente, idMaquina, tokenEmpresa),
fkNucleo INT DEFAULT NULL,
dado FLOAT NOT NULL,
hora DATETIME NOT NULL,
condicao VARCHAR(45),
CONSTRAINT fkLeituraComponente
	FOREIGN KEY (idComponente) REFERENCES Componente(idComponente),
	FOREIGN KEY (fkNucleo) REFERENCES NucleoCPU (idNucleoCPU),
	FOREIGN KEY (tokenEmpresa) REFERENCES Componente(tokenEmpresa),
	FOREIGN KEY (idMaquina) REFERENCES Componente(idMaquina)
);

INSERT IGNORE INTO Cliente (tokenEmpresa, nomeEmpresa, cnpj, telefone) VALUES
	(123456789, 'EmpresaXPTO', '01234567891234', '11975321122');

    

    
    

    
    

    



