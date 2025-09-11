import sys
import os
import time
import threading
import socket
import platform

import psutil as p
import datetime as dt
from mysql.connector import connect, Error
from tabulate import tabulate
from dotenv import load_dotenv

load_dotenv()
inserir_no_banco = False
monitoramento = False
token_empresa = os.getenv("TOKEN_EMPRESA")
id_maquina = os.getenv("ID_MAQUINA")

config = {
      'user': os.getenv("USER_DB"),
      'password': os.getenv("PASSWORD_DB"),
      'host': os.getenv("HOST_DB"),
      'database': os.getenv("DATABASE_DB")
    }

def executar_query(query):
    global config
    try:
        db = connect(**config)
        if db.is_connected():            
            with db.cursor() as cursor:
                cursor.execute(query)
                resultado = cursor.fetchall() 
                db.commit()

            
            cursor.close()
            db.close()
            return resultado
    
    except Error as e:
        print('Error to connect with MySQL -', e) 
        print("Erro ao se conectar com o Banco de dados... Encerrando Aplicação...")
        time.sleep(2)
        sys.exit(1)

def definir_maquina():
    global token_empresa, id_maquina
    executar_query(f"INSERT IGNORE INTO Maquina (idMaquina, TokenEmpresa, nomeMaquina, SO) VALUES ({id_maquina}, {token_empresa}, '{socket.gethostname()}', '{platform.platform()}');")

def definir_componentes():
    global token_empresa, id_maquina
    executar_query(f"INSERT IGNORE INTO Componente (idComponente, idMaquina, TokenEmpresa, nomeComponente, unidadeDeMedida, parametro) VALUES (1, {id_maquina}, {token_empresa}, 'CPU', '%', 80), (2, {id_maquina}, {token_empresa}, 'Memória', '%', 80), (3, {id_maquina}, {token_empresa}, 'Disco', '%', 80);")

def definir_nucleos():
    global token_empresa, id_maquina
    nucleos_fisicos = p.cpu_count(logical=True)
    for i in range(1, nucleos_fisicos + 1):
        executar_query(f"INSERT IGNORE INTO NucleoCPU (idNucleoCPU, idMaquina, TokenEmpresa, idCPU) VALUES ({i}, {id_maquina}, {token_empresa}, 1)")


def coletar_e_inserir_dados():
    global inserir_no_banco, token_empresa, id_maquina
    while inserir_no_banco:
        cpu = p.cpu_percent(interval=10, percpu=True)
        memoria_usada = p.virtual_memory().percent
        if(os.name == 'nt'):
            disco_usado = p.disk_usage("C:\\").percent
        else:
            disco_usado = p.disk_usage("/").percent
        horario = str(dt.datetime.now())
        lista_memoria = (memoria_usada, disco_usado)
        for i in range(0, len(cpu)):
            executar_query(f"INSERT INTO Leitura (idComponente, idMaquina, TokenEmpresa, dado, dthCaptura, fkNucleo) VALUES (1,  {id_maquina}, {token_empresa}, {cpu[i]}, '{horario}', {i + 1})")

        for i in range(0, len(lista_memoria)):
            executar_query(f"INSERT INTO Leitura (idComponente, idMaquina, TokenEmpresa, dado, dthCaptura) VALUES ({i + 2},  {id_maquina}, {token_empresa}, {lista_memoria[i]}, '{horario}')")
    
def barra_progresso(valor, tipo='percent', tamanho=30):
    if tipo == 'percent':
        valor = min(valor, 100)
        preenchido = int((valor / 100) * tamanho)
        barra = "█" * preenchido + "░" * (tamanho - preenchido)
        return f"{barra} {valor:.1f}%"
    return ""   

definir_maquina()
definir_componentes()
definir_nucleos()

query_monitoramento = f"""
SELECT 
    DATE_FORMAT(dthCaptura, '%d/%m/%Y %H:%i:%s'),
    SUM(CASE WHEN idComponente = 1  THEN (ROUND(dado/(SELECT COUNT(*) FROM NucleoCPU WHERE idMaquina = {id_maquina}),2)) END) AS "cpu",
    MAX(CASE WHEN idComponente = 2  THEN ROUND(dado, 2) END) AS "ram",
    MAX(CASE WHEN idComponente = 3 THEN ROUND(dado, 2) END) AS "disco"
FROM Leitura
WHERE idMaquina = {id_maquina} AND TokenEmpresa = {token_empresa}
GROUP BY dthCaptura
ORDER BY dthCaptura DESC
LIMIT"""

query_dados_maquina = executar_query(f"SELECT nomeMaquina, SO FROM Maquina WHERE idMaquina = {id_maquina} AND TokenEmpresa = {token_empresa};") 

try:
    while True:
        print(f"""
MVP CAPTURA DE DADOS SPRINT1 - INFRAFLOW
Nome da Máquina: {query_dados_maquina[0][0]} 
Sistema Operacional: {query_dados_maquina[0][1]}
O que você deseja fazer? (digite o comando)
COMANDOS ACEITOS:
capOn    | iniciar captura de dados 
capOff   | parar captura de dados
realtime | visualizar dados em tempo real
view     | visualizar dados capturados 
viewCPU  | visualizar dados capturados da CPU por núcleo(N)
end      | encerrar aplicação
    """)
        comando = input("Comando: ")
        
        if comando == "capOn":
            if query_dados_maquina[0][0] == socket.gethostname():
                if inserir_no_banco: 
                    print("A captura e inserção já está sendo realizada")
                    time.sleep(2)
                else:
                    inserir_no_banco = True
                    thread = threading.Thread(target=coletar_e_inserir_dados)
                    thread.start()
                    print("Capturando novos dados e inserindo no banco de dados...")
            else:
                print(f"Apenas operações de visualização de dados estão disponíveis\nSomente a máquina cadastrada com ID {id_maquina}: {query_dados_maquina[0][0]} pode realizar capturas")
            time.sleep(2)

        elif comando == "capOff":
            if inserir_no_banco:
                inserir_no_banco = False
                print("Encerrando captura e inserção de dados...")
            else:
                print("A captura e inserção de dados já está desligada")
            time.sleep(2)   

        elif comando == "view":
            try:
                linhas = int(input("Quantos registros exibir?(Do mais recente até o mais antigo) "))
            except:
                print("Quantidade de registros inválida... Recomeçando...")
                time.sleep(2)
                continue
            table = tabulate(executar_query(f"{query_monitoramento} {linhas};"),
            headers=["horário", "cpu(%)", "ram(%)", "disco(%)"], 
            tablefmt="grid"
            )
            print(table)
            print("Recomeçando...")
            time.sleep(2)
        
        elif comando == "viewCPU":
            try:
                linhas = int(input("Quantos registros exibir?(Do mais recente até o mais antigo) "))
            except:
                print("Quantidade de registros inválida... Recomeçando...")
                time.sleep(2)
                continue
            query_nucleos = ""
            cabecalho = ["horário"]

            #Montando query com base no número de núcleos da máquina
            for i in range(1, p.cpu_count(logical=True) + 1):
                if i == p.cpu_count(logical=True):
                    query_nucleos = query_nucleos + f"MAX(CASE WHEN fkNucleo = {i} THEN CONCAT(ROUND(dado, 2), '%') END) AS 'Núcleo_{i}' FROM Leitura WHERE idMaquina = {id_maquina} AND TokenEmpresa = {token_empresa} GROUP BY dthCaptura ORDER BY dthCaptura LIMIT {linhas}"
                    cabecalho.append(f"N{i}")
                else:
                    query_nucleos = query_nucleos + f"MAX(CASE WHEN fkNucleo = {i} THEN CONCAT(ROUND(dado, 2), '%') END) AS 'Núcleo_{i}', "
                    cabecalho.append(f"N{i}")
            table = tabulate(executar_query(f"SELECT DATE_FORMAT(dthCaptura, '%d/%m/%Y %H:%i:%s'), {query_nucleos}"),
            headers = cabecalho, 
            tablefmt="grid"
            )
            print(table)
            print("Recomeçando...")
            time.sleep(2)

        elif comando == "realtime":
            linhas = 0
            print("MONITORAMENTO EM TEMPO REAL - APERTE CTRL + C PARA SAIR:")
            monitoramento = True
            try:
                while monitoramento:
                    time.sleep(5)
                    dados = executar_query(f"{query_monitoramento} 1;")
                    if dados != []:
                        dados = dados[0]
                    else:
                        print("Não há dados de captura")
                        monitoramento = False
                        break
                    if None in dados:
                        continue
                    msg = f"\nMomento da Captura: {dados[0]}\n\nCPU:   {barra_progresso(dados[1])}\n\nRAM:   {barra_progresso(dados[2])}\n\nDISCO: {barra_progresso(dados[3])}"
                    print(msg)
                    linhas = msg.count("\n") + 1
                    sys.stdout.write("\033[F" * linhas)  
                    sys.stdout.write("\033[K" * linhas)  
            except:
                monitoramento = False
                print("\n" * linhas)
                print("Encerrando Monitoramento...")
                time.sleep(2)      

        elif comando == "end":
            if inserir_no_banco:
                inserir_no_banco = False
                print("Encerrando captura e inserção de dados...")
            print("Encerrando Aplicação...")
            break

        else:
            print("Comando inválido... Recomeçando...")
            time.sleep(2)
except:
    if inserir_no_banco:
        inserir_no_banco = False
        print("\nEncerrando captura e inserção de dados...")
    print("Encerrando Aplicação...")

