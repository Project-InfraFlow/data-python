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

load_dotenv(override=True)  # garante que o .env do diretório atual seja lido e sobrescreva o ambiente
inserir_no_banco = False
monitoramento = False
token_empresa = os.getenv("TOKEN_EMPRESA")
id_maquina = os.getenv("ID_MAQUINA")

config = {
      'user': os.getenv("USER_DB"),
      'password': os.getenv("PASSWORD_DB"),
      'host': os.getenv("HOST_DB"),
      'port': int(os.getenv("PORT_DB", "3306")),  # <— acrescentado
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
    executar_query(
        f"""INSERT INTO maquina (id_maquina, fk_empresa_maquina, nome_maquina, so, localizacao, km)
            VALUES ({id_maquina}, {token_empresa}, '{socket.gethostname()}', '{platform.platform()}', 'N/A', 'N/A')
            ON DUPLICATE KEY UPDATE
              nome_maquina=VALUES(nome_maquina),
              so=VALUES(so),
              fk_empresa_maquina=VALUES(fk_empresa_maquina);"""
    )

def definir_componentes():
    global token_empresa, id_maquina
    existentes = executar_query(f"SELECT nome_componente FROM componente WHERE fk_id_maquina = {id_maquina};")
    existentes = [row[0] for row in existentes]
    padrao = ['CPU', 'RAM', 'Disco']

    for comp in padrao:
        if comp not in existentes:
            executar_query(f"INSERT INTO componente (fk_id_maquina, nome_componente, unidade_de_medida) VALUES ({id_maquina}, '{comp}', '%');")

def definir_nucleos():
    global token_empresa, id_maquina
    nucleos_fisicos = p.cpu_count(logical=True)
    # obter id do componente CPU para esta máquina
    id_cpu_comp = executar_query(f"SELECT id_componente FROM componente WHERE fk_id_maquina = {id_maquina} AND nome_componente = 'CPU';")
    if not id_cpu_comp:
        return
    id_cpu_comp = id_cpu_comp[0][0] 
    nucleos_existentes = executar_query(
        f"SELECT COUNT(*) FROM nucleo_cpu WHERE fk_id_componente = {id_cpu_comp} AND fk_id_maquina = {id_maquina};"
    )
    total_existentes = nucleos_existentes[0][0] if nucleos_existentes else 0

    for _ in range(total_existentes + 1, nucleos_fisicos + 1):
        executar_query(
            f"INSERT INTO nucleo_cpu (fk_id_componente, fk_id_maquina) VALUES ({id_cpu_comp}, {id_maquina});"
        )

def coletar_e_inserir_dados():
    global inserir_no_banco, token_empresa, id_maquina
    # capturar ids dos componentes
    comp_rows = executar_query(f"SELECT nome_componente, id_componente FROM componente WHERE fk_id_maquina = {id_maquina}")
    comp_map = {nome: cid for (nome, cid) in comp_rows}
    id_cpu_comp = comp_map.get('CPU')
    id_ram_comp = comp_map.get('RAM')
    id_disco_comp = comp_map.get('Disco')
    # capturar ids dos núcleos desta máquina (em ordem)
    nucleos_ids = [row[0] for row in executar_query(f"SELECT id_nucleo FROM nucleo_cpu WHERE fk_id_maquina = {id_maquina} ORDER BY id_nucleo")]
    while inserir_no_banco:
        cpu = p.cpu_percent(interval=3, percpu=True)
        memoria_usada = p.virtual_memory().percent
        if(os.name == 'nt'):
            disco_usado = p.disk_usage("C:\\").percent
        else:
            disco_usado = p.disk_usage("/").percent
        horario = str(dt.datetime.now())
        lista_memoria = (memoria_usada, disco_usado)
        for i in range(0, len(cpu)):
            id_nucleo_ref = nucleos_ids[i] if i < len(nucleos_ids) else "NULL"
            executar_query(f"INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura, id_nucleo) VALUES ({id_cpu_comp}, {id_maquina}, {cpu[i]}, '{horario}', {id_nucleo_ref})")

        # RAM (2) e Disco (3)
        if id_ram_comp is not None:
            executar_query(f"INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura) VALUES ({id_ram_comp}, {id_maquina}, {lista_memoria[0]}, '{horario}')")
        if id_disco_comp is not None:
            executar_query(f"INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura) VALUES ({id_disco_comp}, {id_maquina}, {lista_memoria[1]}, '{horario}')")
    
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
    DATE_FORMAT(l.data_hora_captura, '%d/%m/%Y %H:%i:%s') AS horario,
    SUM(CASE WHEN c.nome_componente = 'CPU' THEN ROUND(l.dados_float / (SELECT COUNT(*) FROM nucleo_cpu WHERE fk_id_maquina = l.fk_id_maquina), 2) ELSE 0 END) AS cpu,
    MAX(CASE WHEN c.nome_componente = 'RAM' THEN ROUND(l.dados_float, 2) END) AS ram,
    MAX(CASE WHEN c.nome_componente = 'Disco' THEN ROUND(l.dados_float, 2) END) AS disco
FROM leitura l
JOIN componente c ON l.fk_id_componente = c.id_componente
WHERE l.fk_id_maquina = 1
GROUP BY l.data_hora_captura
ORDER BY l.data_hora_captura DESC
LIMIT"""

query_dados_maquina = executar_query(f"SELECT nome_maquina, so FROM maquina WHERE id_maquina = {id_maquina} AND fk_empresa_maquina = {token_empresa};") 

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

            # mapear ids dos núcleos desta máquina (ordem)
            nucleos_ids = [row[0] for row in executar_query(f"SELECT id_nucleo FROM nucleo_cpu WHERE fk_id_maquina = {id_maquina} ORDER BY id_nucleo")]
            cabecalho = ["horário"] + [f"N{i+1}" for i in range(len(nucleos_ids))]

            # id do componente CPU
            id_cpu_comp = executar_query(f"SELECT id_componente FROM componente WHERE fk_id_maquina = {id_maquina} AND nome_componente='CPU' LIMIT 1;")
            id_cpu_comp = id_cpu_comp[0][0] if id_cpu_comp else 0

            seletores = []
            for idx, nid in enumerate(nucleos_ids, start=1):
                seletores.append(f"MAX(CASE WHEN id_nucleo = {nid} AND fk_id_componente = {id_cpu_comp} THEN CONCAT(ROUND(dados_float, 2), '%') END) AS 'Núcleo_{idx}'")
            seletores_sql = ", ".join(seletores)

            table = tabulate(
                executar_query(
                    f"SELECT DATE_FORMAT(data_hora_captura, '%d/%m/%Y %H:%i:%s'), {seletores_sql} "
                    f"FROM leitura WHERE fk_id_maquina = {id_maquina} "
                    f"GROUP BY data_hora_captura ORDER BY data_hora_captura DESC LIMIT {linhas}"
                ),
                headers=cabecalho, 
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
