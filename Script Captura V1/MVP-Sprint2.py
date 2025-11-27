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
from flask import Flask, jsonify

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

app = Flask(__name__)

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

def inserir_alerta(componente_id, descricao, status=1):
    parametro = executar_query("SELECT id_parametro_alerta FROM parametro_alerta LIMIT 1")
    if parametro:
        parametro_id = parametro[0][0]
        leitura = executar_query(f"""
            SELECT id_leitura FROM leitura 
            WHERE fk_id_componente = {componente_id} 
            ORDER BY data_hora_captura DESC LIMIT 1
        """)
        if leitura:
            leitura_id = leitura[0][0]
            executar_query(f"""
                INSERT INTO alerta (fk_id_leitura, fk_id_componente, fk_parametro_alerta, descricao, status_alerta)
                VALUES ({leitura_id}, {componente_id}, {parametro_id}, '{descricao}', {status})
            """)

@app.route('/alertas/operacionais', methods=['GET'])
def get_alertas_operacionais():
    try:
        db = connect(**config)
        if db.is_connected():
            with db.cursor() as cursor:
                query = """
                SELECT 
                    a.descricao as mensagem,
                    l.data_hora_captura as timestamp,
                    c.nome_componente as origem
                FROM alerta a
                JOIN leitura l ON a.fk_id_leitura = l.id_leitura
                JOIN componente c ON a.fk_id_componente = c.id_componente
                WHERE l.data_hora_captura >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY l.data_hora_captura DESC
                LIMIT 50
                """
                cursor.execute(query)
                alertas = cursor.fetchall()
                
                alertas_formatados = []
                for alerta in alertas:
                    alertas_formatados.append({
                        'mensagem': alerta[0],
                        'timestamp': alerta[1].isoformat() if alerta[1] else None,
                        'origem': alerta[2]
                    })
                
                db.close()
                return jsonify(alertas_formatados)
                
    except Error as e:
        print('Erro ao buscar alertas operacionais:', e)
        return jsonify([])

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

            # CPU
            if max_cpu > 95:
                mensagem = f"[CRÍTICO] CPU acima de 95% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {max_cpu:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_cpu_comp, mensagem)
            elif max_cpu > 85:
                mensagem = f"[ALTA] CPU acima de 85% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {max_cpu:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_cpu_comp, mensagem)
            elif max_cpu > 70:
                mensagem = f"[ATENÇÃO] CPU acima de 70% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {max_cpu:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_cpu_comp, mensagem)
            elif max_cpu > 50:
                mensagem = f"[MONITORAR] CPU acima de 50% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {max_cpu:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_cpu_comp, mensagem)

            # Memória
            if memoria_usada > 95:
                mensagem = f"[CRÍTICO] Memória acima de 95% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {memoria_usada:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_ram_comp, mensagem)
            elif memoria_usada > 85:
                mensagem = f"[ALTA] Memória acima de 85% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {memoria_usada:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_ram_comp, mensagem)
            elif memoria_usada > 70:
                mensagem = f"[ATENÇÃO] Memória acima de 70% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {memoria_usada:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_ram_comp, mensagem)
            elif memoria_usada > 50:
                mensagem = f"[MONITORAR] Memória acima de 50% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {memoria_usada:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_ram_comp, mensagem)

            # Disco
            if disco_usado > 95:
                mensagem = f"[CRÍTICO] Disco acima de 95% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {disco_usado:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_disco_comp, mensagem)
            elif disco_usado > 85:
                mensagem = f"[ALTA] Disco acima de 85% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {disco_usado:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_disco_comp, mensagem)
            elif disco_usado > 70:
                mensagem = f"[ATENÇÃO] Disco acima de 70% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {disco_usado:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_disco_comp, mensagem)
            elif disco_usado > 50:
                mensagem = f"[MONITORAR] Disco acima de 50% no {NOME_PORTICO} (id {id_maquina}). Valor atual: {disco_usado:.2f}%."
                enviar_alerta_slack(mensagem)
                inserir_alerta(id_disco_comp, mensagem)

            print(f" Dados inseridos às {horario}")
        except KeyboardInterrupt:
            print("\n Captura encerrada manualmente.")
            break
        except Exception as e:
            print(f" Erro durante captura: {e}")
            time.sleep(1)

if __name__ == "__main__":
    print("Inicializando configurações da máquina e componentes...")
    definir_maquina()
    definir_componentes()
    definir_nucleos()
    
    def iniciar_servidor():
        app.run(host='0.0.0.0', port=3333, debug=False)
    
    flask_thread = threading.Thread(target=iniciar_servidor, daemon=True)
    flask_thread.start()
    print("Servidor Flask iniciado na porta 3333")
    print("Endpoint de alertas disponível em: http://localhost:3333/alertas/operacionais")
    
    coletar_dados()