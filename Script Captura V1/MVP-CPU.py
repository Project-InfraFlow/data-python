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

def medir_latencia_cpu():
    cpu_times = p.cpu_times()
    total = cpu_times.user + cpu_times.system + cpu_times.idle
    if total == 0:
        return 0
    return round((cpu_times.idle / total) * 1000, 2)

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
        print("Erro:", e)

def buscar_maquina(nome):
    db = get_connection()
    cursor = db.cursor()
    cursor.execute("SELECT id_maquina FROM maquina WHERE nome_maquina = %s", (nome,))
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row["id_maquina"] if row else None

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

def iniciar_captura():
    NOME_MAQUINA = "ECV-APP-01"
    id_maquina = buscar_maquina(NOME_MAQUINA)
    if not id_maquina:
        print("Máquina não encontrada:", NOME_MAQUINA)
        return

    comps = buscar_componentes(id_maquina)
    id_cpu = None
    id_proc = None
    id_lat = None

    for c in comps:
        if c["nome_componente"] == "CPU":
            id_cpu = c["id_componente"]
        elif c["nome_componente"] == "Processos":
            id_proc = c["id_componente"]
        elif c["nome_componente"] == "Latência CPU":
            id_lat = c["id_componente"]

    nucleos_cpu = buscar_nucleos(id_maquina, id_cpu)

    print("CAPTURANDO DADOS DA MÁQUINA:", NOME_MAQUINA)

    while True:
        horario = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cpu_nucleos = p.cpu_percent(interval=1, percpu=True)
        total_processos = len(p.pids())
        lat = medir_latencia_cpu()

        for i, valor in enumerate(cpu_nucleos):
            inserir_leitura(id_cpu, id_maquina, valor, horario, id_nucleo=nucleos_cpu[i])

        inserir_leitura(id_proc, id_maquina, total_processos, horario)

        processos_nucleo = {}
        for proc in p.process_iter(["pid", "name"]):
            try:
                n = proc.cpu_num()
                processos_nucleo[n] = processos_nucleo.get(n, 0) + 1
            except:
                pass

        for i, id_nucleo in enumerate(nucleos_cpu):
            quantidade = processos_nucleo.get(i, 0)
            inserir_leitura(id_proc, id_maquina, quantidade, horario, id_nucleo=id_nucleo)

        inserir_leitura(id_lat, id_maquina, lat, horario)
        time.sleep(15)

iniciar_captura()
