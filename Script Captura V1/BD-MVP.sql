CREATE DATABASE IF NOT EXISTS Infraflow;
USE Infraflow;

CREATE TABLE IF NOT EXISTS Componente(
idComponente INT PRIMARY KEY,
nomeComponente VARCHAR(45) NOT NULL,
UM VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS NucleoCPU(
idNucleoCPU INT AUTO_INCREMENT,
idCPU INT,
CONSTRAINT PkComposta
	PRIMARY KEY (idNucleoCPU, idCPU),
CONSTRAINT fkNucleoCPUComponente
	FOREIGN KEY (IdCPU) REFERENCES Componente(idComponente)
);

CREATE TABLE IF NOT EXISTS Leitura(
idLeitura INT AUTO_INCREMENT,
idComponente INT,
CONSTRAINT pkComposta
	PRIMARY KEY (idLeitura, idComponente),
fkNucleo INT DEFAULT NULL,
dado FLOAT NOT NULL,
hora DATETIME NOT NULL,
condicao VARCHAR(45),
CONSTRAINT fkLeituraComponente
	FOREIGN KEY (idComponente) REFERENCES Componente(idComponente),
CONSTRAINT fkLeituraNucleoCPU 
	FOREIGN KEY (fkNucleo) REFERENCES nucleoCPU (idNucleoCPU)
);

INSERT IGNORE INTO Componente (idComponente, nomeComponente, UM) VALUES
	(1, "CPU", "%"),
    (2, "Memória", "%"),
    (3, "Disco", "%");
    
CREATE VIEW Monitoramento AS
	SELECT 
		hora,
		SUM(CASE WHEN idComponente = 1  THEN (ROUND(dado/(SELECT COUNT(*) FROM NucleoCPU),2)) END) AS "cpu",
		MAX(CASE WHEN idComponente = 2  THEN ROUND(dado, 2) END) AS "ram",
		MAX(CASE WHEN idComponente = 3 THEN ROUND(dado, 2) END) AS "disco"
	FROM Leitura
	GROUP BY hora
	ORDER BY hora DESC;
    
    

    



