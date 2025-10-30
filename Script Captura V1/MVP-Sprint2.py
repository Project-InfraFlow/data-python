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

                # só tenta fetchall se for um SELECT
                if query.strip().lower().startswith("select"):
                    resultado = cursor.fetchall()
                else:
                    resultado = None

                db.commit()

            db.close()
            return resultado
    except Error as e:
        print('Erro ao conectar ou executar query:', e)
        time.sleep(2)

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

def coletar_dados():
    global token_empresa, id_maquina
    comp_rows = executar_query(f"SELECT nome_componente, id_componente FROM componente WHERE fk_id_maquina = {id_maquina}")
    comp_map = {nome: cid for (nome, cid) in comp_rows}
    id_cpu_comp = comp_map.get('CPU')
    id_ram_comp = comp_map.get('RAM')
    id_disco_comp = comp_map.get('Disco')
    nucleos_ids = [row[0] for row in executar_query(f"SELECT id_nucleo FROM nucleo_cpu WHERE fk_id_maquina = {id_maquina} ORDER BY id_nucleo")]

    print(" Iniciando captura automática de dados...")
    while True:
        try:
            cpu = p.cpu_percent(interval=10, percpu=True)
            memoria_usada = p.virtual_memory().percent
            disco_usado = p.disk_usage("C:\\" if os.name == 'nt' else "/").percent
            horario = str(dt.datetime.now())

            for i in range(0, len(cpu)):
                id_nucleo_ref = nucleos_ids[i] if i < len(nucleos_ids) else "NULL"
                executar_query(f"""
                    INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura, id_nucleo)
                    VALUES ({id_cpu_comp}, {id_maquina}, {cpu[i]}, '{horario}', {id_nucleo_ref});
                """)

            if id_ram_comp is not None:
                executar_query(f"""
                    INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura)
                    VALUES ({id_ram_comp}, {id_maquina}, {memoria_usada}, '{horario}');
                """)
            if id_disco_comp is not None:
                executar_query(f"""
                    INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura)
                    VALUES ({id_disco_comp}, {id_maquina}, {disco_usado}, '{horario}');
                """)

            print(f" Dados inseridos às {horario}")
        except KeyboardInterrupt:
            print("\n Captura encerrada manualmente.")
            break
        except Exception as e:
            print(f" Erro durante captura: {e}")
            time.sleep(5)

# Execução automática
if __name__ == "__main__":
    print("Inicializando configurações da máquina e componentes...")
    definir_maquina()
    definir_componentes()
    definir_nucleos()
    coletar_dados()