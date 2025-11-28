import time
import speedtest
import ping3
import statistics
import os 
from mysql.connector import connect, Error
from dotenv import load_dotenv 

load_dotenv()

MAQUINAS = [1, 2, 3, 4, 5]

COMPONENTE_REDE_ID = 4

def get_connection():

    config = {
      'user': os.getenv("USER_DB"),
      'password': os.getenv("PASSWORD_DB"),
      'host': os.getenv("HOST_DB"),
      'port': int(os.getenv("PORT_DB", "3306")), 
      'database': os.getenv("DATABASE_DB")
    }

    if not all([config['user'], config['password'], config['host'], config['database']]):
        print("Erro: Variáveis de ambiente não configuradas corretamente.")
        return None

    try:
        connection = connect(**config)
        if connection.is_connected():
            print("Conectado ao MySQL.")
            return connection
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None


def insert_leitura(connection, fk_id_componente, fk_id_maquina, dados_float, dados_texto):

    insert_query = """
    INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, dados_texto, data_hora_captura)
    VALUES (%s, %s, %s, %s, NOW())
    """

    data = (fk_id_componente, fk_id_maquina, dados_float, dados_texto)

    try:
        cursor = connection.cursor()
        cursor.execute(insert_query, data)
        connection.commit()
    except Error as e:
        print(f"❌ Erro ao inserir dados: {e}")
        connection.rollback()
    finally:
        if cursor:
            cursor.close()


def measure_network_metrics(target_host="google.com"):

    latencies = []
    packet_loss_count = 0
    total_pings = 5

    for _ in range(total_pings):
        try:
            delay = ping3.ping(target_host, unit='ms', timeout=2)
            if delay is not None:
                latencies.append(delay)
            else:
                packet_loss_count += 1
        except Exception:
            packet_loss_count += 1

    if latencies:
        avg_latency = statistics.mean(latencies)
        jitter_list = [abs(latencies[i] - latencies[i-1]) for i in range(1, len(latencies))]
        jitter = statistics.mean(jitter_list) if jitter_list else 0.0
    else:
        avg_latency = 0.0
        jitter = 0.0

    packet_loss_rate = (packet_loss_count / total_pings) * 100

    download_speed_mbps = 0.0
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed_bytes = st.download()
        download_speed_mbps = round(download_speed_bytes / (10**6), 2)
    except Exception as e:
        print(f"[ERRO SPEEDTEST] {e}")


    return {
        "latencia_ms": round(avg_latency, 2),
        "jitter_ms": round(jitter, 2),
        "perda_pacotes_%": round(packet_loss_rate, 2),
        "velocidade_download_mbps": download_speed_mbps
    }


def continuous_monitoring(interval_seconds=10):

    connection = get_connection()
    if not connection:
        return

    print(f"Monitoramento iniciado para máquinas: {MAQUINAS}")
    print("-" * 60)

    try:
        while True:

            metrics = measure_network_metrics()

            print(f"Latência: {metrics['latencia_ms']} ms | "
                  f"Jitter: {metrics['jitter_ms']} ms | "
                  f"Perda: {metrics['perda_pacotes_%']}% | "
                  f"Download: {metrics['velocidade_download_mbps']} Mbps")

            for maquina_id in MAQUINAS:

                insert_leitura(connection, COMPONENTE_REDE_ID, maquina_id, metrics['latencia_ms'], "Latencia Media (ms)")
                insert_leitura(connection, COMPONENTE_REDE_ID, maquina_id, metrics['jitter_ms'], "Jitter (ms)")
                insert_leitura(connection, COMPONENTE_REDE_ID, maquina_id, metrics['perda_pacotes_%'], "Perda de Pacotes (%)")
                insert_leitura(connection, COMPONENTE_REDE_ID, maquina_id, metrics['velocidade_download_mbps'], "Velocidade Download (Mbps)")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("Monitoramento interrompido.")
    finally:
        if connection and connection.is_connected():
            connection.close()
            print("🔌 Conexão MySQL encerrada.")


if __name__ == "__main__":
    continuous_monitoring(interval_seconds=5)
