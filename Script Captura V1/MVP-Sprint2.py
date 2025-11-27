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
import urllib.request
import json

load_dotenv(override=True)
inserir_no_banco = False
monitoramento = False
token_empresa = os.getenv("TOKEN_EMPRESA")
id_maquina = os.getenv("ID_MAQUINA")
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"
NOME_PORTICO = "Pórtico - INFRA-EDGE-01-Itápolis (SP-333)"

config = {
      'user': os.getenv("USER_DB"),
      'password': os.getenv("PASSWORD_DB"),
      'host': os.getenv("HOST_DB"),
      'port': int(os.getenv("PORT_DB", "3306")),
      'database': os.getenv("DATABASE_DB")
    }

def enviar_alerta_slack(mensagem: str):
    global SLACK_WEBHOOK_URL
    if not SLACK_WEBHOOK_URL:
        return
    try:
        dados = json.dumps({"text": mensagem}).encode("utf-8")
        requisicao = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=dados,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(requisicao, timeout=5)
    except Exception as e:
        print("Erro ao enviar alerta para Slack:", e)

def executar_query(query):
    global config
    try:
        db = connect(**config)
        if db.is_connected():
            with db.cursor() as cursor:
                cursor.execute(query)
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
            VALUES ({id_maquina}, {token_empresa}, '{NOME_PORTICO}', '{platform.platform()}', 'N/A', 'N/A')
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

            max_cpu = max(cpu) if cpu else 0.0

            if max_cpu > 95:
                enviar_alerta_slack(
                    f"[CRÍTICO] CPU acima de 95% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {max_cpu:.2f}%."
                )
            elif max_cpu > 85:
                enviar_alerta_slack(
                    f"[ALTA] CPU acima de 85% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {max_cpu:.2f}%."
                )
            elif max_cpu > 70:
                enviar_alerta_slack(
                    f"[ATENÇÃO] CPU acima de 70% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {max_cpu:.2f}%."
                )
            elif max_cpu > 50:
                enviar_alerta_slack(
                    f"[MONITORAR] CPU acima de 50% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {max_cpu:.2f}%."
                )

            if memoria_usada > 95:
                enviar_alerta_slack(
                    f"[CRÍTICO] Memória acima de 95% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {memoria_usada:.2f}%."
                )
            elif memoria_usada > 85:
                enviar_alerta_slack(
                    f"[ALTA] Memória acima de 85% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {memoria_usada:.2f}%."
                )
            elif memoria_usada > 70:
                enviar_alerta_slack(
                    f"[ATENÇÃO] Memória acima de 70% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {memoria_usada:.2f}%."
                )
            elif memoria_usada > 50:
                enviar_alerta_slack(
                    f"[MONITORAR] Memória acima de 50% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {memoria_usada:.2f}%."
                )

            if disco_usado > 95:
                enviar_alerta_slack(
                    f"[CRÍTICO] Disco acima de 95% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {disco_usado:.2f}%."
                )
            elif disco_usado > 85:
                enviar_alerta_slack(
                    f"[ALTA] Disco acima de 85% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {disco_usado:.2f}%."
                )
            elif disco_usado > 70:
                enviar_alerta_slack(
                    f"[ATENÇÃO] Disco acima de 70% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {disco_usado:.2f}%."
                )
            elif disco_usado > 50:
                enviar_alerta_slack(
                    f"[MONITORAR] Disco acima de 50% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {disco_usado:.2f}%."
                )

            print(f" Dados inseridos às {horario}")
        except KeyboardInterrupt:
            print("\n Captura encerrada manualmente.")
            break
        except Exception as e:
            print(f" Erro durante captura: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print("Inicializando configurações da máquina e componentes...")
    definir_maquina()
    definir_componentes()
    definir_nucleos()
    coletar_dados()
