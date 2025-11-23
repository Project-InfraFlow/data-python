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

load_dotenv(override=True)
inserir_no_banco = False
monitoramento = False
token_empresa = os.getenv("TOKEN_EMPRESA")
id_maquina = os.getenv("ID_MAQUINA")

config = {
    'user': os.getenv("USER_DB"),
    'password': os.getenv("PASSWORD_DB"),
    'host': os.getenv("HOST_DB"),
    'port': int(os.getenv("PORT_DB", "3306")),
    'database': os.getenv("DATABASE_DB")
}

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
            VALUES ({id_maquina}, {token_empresa}, '{socket.gethostname()}', '{platform.platform()}', 'N/A', 'N/A')
            ON DUPLICATE KEY UPDATE
              nome_maquina=VALUES(nome_maquina),
              so=VALUES(so),
              fk_empresa_maquina=VALUES(fk_empresa_maquina);"""
    )

def definir_componentes():
    global token_empresa, id_maquina
    existentes = executar_query(f"SELECT nome_componente FROM componente WHERE fk_id_maquina = {id_maquina};")
    existentes = [row[0] for row in existentes] if existentes else []
    padrao = ['CPU', 'Memória RAM', 'Disco']

    for comp in padrao:
        if comp not in existentes:
            executar_query(f"INSERT INTO componente (fk_id_maquina, nome_componente, unidade_de_medida) VALUES ({id_maquina}, '{comp}', '%');")

def bytes_para_gb(bytes_value):
    return round(bytes_value / (1024 ** 3), 2)

def verificar_alerta_memoria(uso_percent):
    """Verifica se o uso de memória está em estado crítico baseado nos parâmetros"""
    if uso_percent > 84:  # Saturação crítica
        return "CRITICO"
    elif uso_percent > 53:  # Alta utilização
        return "ALTA"
    else:  # Utilização saudável
        return "NORMAL"

def obter_parametro_alerta(uso_percent):
    """Obtém o ID do parâmetro de alerta baseado no uso"""
    parametros = executar_query(f"""
        SELECT id_parametro_alerta, min, max 
        FROM parametro_alerta 
        WHERE {uso_percent} BETWEEN min AND max
        LIMIT 1
    """)
    
    if parametros:
        return parametros[0][0]  # Retorna o id_parametro_alerta
    return None

def registrar_alerta_memoria(uso_percent, id_leitura, id_componente):
    """Registra alerta no banco se necessário"""
    global token_empresa, id_maquina
    
    status = verificar_alerta_memoria(uso_percent)
    
    if status in ["CRITICO", "ALTA"]:
        horario = str(dt.datetime.now())
        id_parametro = obter_parametro_alerta(uso_percent)
        
        if id_parametro:
            # Verifica se já existe um alerta similar nos últimos 5 minutos
            alerta_recente = executar_query(f"""
                SELECT id_alerta FROM alerta 
                WHERE fk_id_componente = {id_componente}
                AND fk_id_leitura = {id_leitura}
                AND TIMESTAMPDIFF(MINUTE, (SELECT data_hora_captura FROM leitura WHERE id_leitura = {id_leitura}), '{horario}') < 5
            """)
            
            if not alerta_recente:
                descricao = f"Uso de memória {uso_percent}% - {status}"
                executar_query(f"""
                    INSERT INTO alerta (fk_id_leitura, fk_id_componente, fk_parametro_alerta, descricao, status_alerta)
                    VALUES ({id_leitura}, {id_componente}, {id_parametro}, '{descricao}', 1);
                """)
                print(f" Alerta registrado: {descricao}")

def coletar_dados_memoria():
    global token_empresa, id_maquina
    
    # Obtém o ID do componente Memória RAM
    comp_rows = executar_query(f"SELECT nome_componente, id_componente FROM componente WHERE fk_id_maquina = {id_maquina}")
    comp_map = {nome: cid for (nome, cid) in comp_rows} if comp_rows else {}
    id_ram_comp = comp_map.get('Memória RAM')
    
    if not id_ram_comp:
        print(" Componente Memória RAM não encontrado. Verifique a configuração.")
        return
    
    print(" Iniciando captura automática de dados de memória...")
    
    while True:
        try:
            # Coleta dados detalhados de memória
            memoria = p.virtual_memory()
            
            uso_percent = memoria.percent
            memoria_livre_gb = bytes_para_gb(memoria.available)
            memoria_total_gb = bytes_para_gb(memoria.total)
            memoria_usada_gb = bytes_para_gb(memoria.used)
            
            horario = str(dt.datetime.now())
            
            # Insere dados principais de uso percentual na tabela leitura
            executar_query(f"""
                INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura)
                VALUES ({id_ram_comp}, {id_maquina}, {uso_percent}, '{horario}');
            """)
            
            # Obtém o ID da leitura recém-inserida
            id_leitura = executar_query("SELECT LAST_INSERT_ID();")
            if id_leitura:
                id_leitura = id_leitura[0][0]
                
                # Registra alertas se necessário
                registrar_alerta_memoria(uso_percent, id_leitura, id_ram_comp)
            
            print(f" Memória - Uso: {uso_percent}%, Livre: {memoria_livre_gb}GB, Total: {memoria_total_gb}GB - {horario}")
            
            time.sleep(30)  # Coleta a cada 30 segundos
            
        except KeyboardInterrupt:
            print("\n Captura de memória encerrada manualmente.")
            break
        except Exception as e:
            print(f" Erro durante captura de memória: {e}")
            time.sleep(5)

def coletar_dados_cpu_disco():
    """Função separada para coletar CPU e Disco"""
    global token_empresa, id_maquina
    
    comp_rows = executar_query(f"SELECT nome_componente, id_componente FROM componente WHERE fk_id_maquina = {id_maquina}")
    comp_map = {nome: cid for (nome, cid) in comp_rows} if comp_rows else {}
    
    id_cpu_comp = comp_map.get('CPU')
    id_disco_comp = comp_map.get('Disco')
    
    # Obtém IDs dos núcleos
    nucleos_ids = []
    if id_cpu_comp:
        nucleos_result = executar_query(f"SELECT id_nucleo FROM nucleo_cpu WHERE fk_id_maquina = {id_maquina} ORDER BY id_nucleo")
        nucleos_ids = [row[0] for row in nucleos_result] if nucleos_result else []
    
    print(" Iniciando captura de CPU e Disco...")
    
    while True:
        try:
            horario = str(dt.datetime.now())
            
            # Coleta CPU
            if id_cpu_comp:
                cpu = p.cpu_percent(interval=1, percpu=True)
                for i in range(0, len(cpu)):
                    id_nucleo_ref = nucleos_ids[i] if i < len(nucleos_ids) else "NULL"
                    executar_query(f"""
                        INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura, id_nucleo)
                        VALUES ({id_cpu_comp}, {id_maquina}, {cpu[i]}, '{horario}', {id_nucleo_ref});
                    """)
            
            # Coleta Disco
            if id_disco_comp:
                disco_usado = p.disk_usage("C:\\" if os.name == 'nt' else "/").percent
                executar_query(f"""
                    INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura)
                    VALUES ({id_disco_comp}, {id_maquina}, {disco_usado}, '{horario}');
                """)
            
            print(f" CPU/Disco inseridos às {horario}")
            time.sleep(60)  # Coleta a cada 60 segundos
            
        except Exception as e:
            print(f" Erro durante captura de CPU/Disco: {e}")
            time.sleep(10)

# Execução automática
if __name__ == "__main__":
    print("Inicializando configurações da máquina e componentes...")
    definir_maquina()
    definir_componentes()
    
    # Inicia threads separadas para memória e CPU/Disco
    thread_memoria = threading.Thread(target=coletar_dados_memoria, daemon=True)
    thread_cpu_disco = threading.Thread(target=coletar_dados_cpu_disco, daemon=True)
    
    thread_memoria.start()
    thread_cpu_disco.start()
    
    print("Monitoramento iniciado em threads separadas...")
    
    try:
        # Mantém o programa principal rodando
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando monitoramento...")