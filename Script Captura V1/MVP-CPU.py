import psutil as p
import time
from datetime import datetime
import pymysql
import os
from dotenv import load_dotenv

load_dotenv(override=True)

config = {
    'user': os.getenv("USER_DB"),
    'password': os.getenv("PASSWORD_DB"),
    'host': os.getenv("HOST_DB"),
    'port': int(os.getenv("PORT_DB", "3306")),
    'database': os.getenv("DATABASE_DB")
}

def get_connection():
    return pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        port=config['port'],
        cursorclass=pymysql.cursors.DictCursor
    )

def medir_tempo_ocioso_cpu():
    idle = p.cpu_times_percent(interval=1).idle
    return round(idle, 2)

def inserir_leitura(id_componente, id_maquina, valor, horario, id_nucleo=None):
    try:
        db = get_connection()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO leitura
            (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura, id_nucleo)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_componente, id_maquina, valor, horario, id_nucleo))
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print("Erro ao inserir leitura:", e)

def buscar_componentes(id_maquina):
    db = get_connection()
    cursor = db.cursor()
    cursor.execute("""
        SELECT id_componente, nome_componente
        FROM componente
        WHERE fk_id_maquina = %s
    """, (id_maquina,))
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return rows

def buscar_nucleos(id_maquina, id_cpu):
    db = get_connection()
    cursor = db.cursor()
    cursor.execute("""
        SELECT id_nucleo
        FROM nucleo_cpu
        WHERE fk_id_maquina = %s AND fk_id_componente = %s
    """, (id_maquina, id_cpu))
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return [r["id_nucleo"] for r in rows]

def criar_componente_processos(id_maquina):
    db = get_connection()
    cursor = db.cursor()
    cursor.execute("""
        SELECT id_componente 
        FROM componente 
        WHERE fk_id_maquina = %s AND nome_componente = 'Processos'
    """, (id_maquina,))
    row = cursor.fetchone()

    if row:
        id_proc = row["id_componente"]
    else:
        cursor.execute("""
            INSERT INTO componente
            (fk_id_maquina, nome_componente, unidade_de_medida)
            VALUES (%s, 'Processos', 'qtd')
        """, (id_maquina,))
        db.commit()
        id_proc = cursor.lastrowid
        print("Componente 'Processos' criado:", id_proc)

    cursor.close()
    db.close()
    return id_proc

def iniciar_captura():
    ID_MAQUINA = 1 

    print("INICIANDO SCRIPT")
    print(f"CAPTURANDO DADOS DA MÁQUINA ID: {ID_MAQUINA}")

    comps = buscar_componentes(ID_MAQUINA)

    id_cpu = None
    id_proc = None
    id_idle = None

    for c in comps:
        nome = (c["nome_componente"] or "").strip().lower()

        if nome == "cpu":
            id_cpu = c["id_componente"]
        elif nome == "processos":
            id_proc = c["id_componente"]
        elif nome in ("cpu idle", "cpu_idle", "cpuidle", "cpu idle %"):
            id_idle = c["id_componente"]

    if id_cpu is None:
        print("Nenhum componente 'CPU' encontrado para a máquina ID:", ID_MAQUINA)
        return

    if id_proc is None:
        id_proc = criar_componente_processos(ID_MAQUINA)

    nucleos_cpu = buscar_nucleos(ID_MAQUINA, id_cpu)

    if id_idle is None:
        print("Nenhum componente de 'CPU Idle' encontrado. Leituras de Idle não serão gravadas.")

    while True:
        horario = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cpu_info = p.cpu_times_percent(interval=0)  

        tempo_ocioso = round(cpu_info.idle, 2)
        cpu_total = round(100 - tempo_ocioso, 2)

        total_processos = len(p.pids())

        inserir_leitura(id_cpu, ID_MAQUINA, cpu_total, horario)
        inserir_leitura(id_proc, ID_MAQUINA, total_processos, horario)

        if id_idle is not None:
            inserir_leitura(id_idle, ID_MAQUINA, tempo_ocioso, horario)

        time.sleep(3)

if __name__ == "__main__":
    iniciar_captura()
