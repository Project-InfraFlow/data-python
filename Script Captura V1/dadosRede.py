import time
import speedtest
import ping3
import statistics
import os 
from mysql.connector import connect, Error

MAQUINA_ID = 1
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
        print("Erro: As variáveis de ambiente do banco de dados não estão configuradas corretamente.")
        print("Certifique-se de definir USER_DB, PASSWORD_DB, HOST_DB e DATABASE_DB.")
        return None

    try:
        connection = connect(**config) 
        if connection.is_connected():
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
        print(f"Erro ao inserir dados na tabela 'leitura': {e}")
        connection.rollback()
    finally:
        if cursor:
            cursor.close()

def measure_network_metrics(target_host="google.com"):
    # Código desta função permanece inalterado
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
    except speedtest.ConfigRetrievalError:
        pass
    except Exception as e:
        print(f"Erro no speedtest: {e}")

    return {
        "latencia_ms": round(avg_latency, 2),
        "jitter_ms": round(jitter, 2),
        "perda_pacotes_%": round(packet_loss_rate, 2),
        "velocidade_download_mbps": download_speed_mbps
    }

def continuous_monitoring(interval_seconds=30):
    
    print(f"Monitoramento contínuo iniciado para Máquina ID {MAQUINA_ID}. Intervalo: {interval_seconds} segundos.")
    print("-" * 50)
    
    connection = get_connection()
    if not connection:
        return

    try:
        while True:
            timestamp_start = time.strftime("%Y-%m-%d %H:%M:%S")
            metrics = measure_network_metrics()

            print(f"[{timestamp_start}] Lat: {metrics['latencia_ms']}ms, Jitter: {metrics['jitter_ms']}ms, Perda: {metrics['perda_pacotes_%']}%, Download: {metrics['velocidade_download_mbps']} Mbps")

            common_args = {
                "connection": connection,
                "fk_id_componente": COMPONENTE_REDE_ID,
                "fk_id_maquina": MAQUINA_ID,
            }

            insert_leitura(**common_args, dados_float=metrics['latencia_ms'],              dados_texto="Latencia Media (ms)")
            insert_leitura(**common_args, dados_float=metrics['jitter_ms'],                dados_texto="Jitter (ms)")
            insert_leitura(**common_args, dados_float=metrics['perda_pacotes_%'],          dados_texto="Perda de Pacotes (%)")
            insert_leitura(**common_args, dados_float=metrics['velocidade_download_mbps'], dados_texto="Velocidade Download (Mbps)")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nMonitoramento interrompido pelo usuário.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado durante o monitoramento: {e}")
    finally:
        if connection and connection.is_connected():
            connection.close()
            print("Conexão ao MySQL fechada.")

if __name__ == "__main__":
    continuous_monitoring(interval_seconds=3)
