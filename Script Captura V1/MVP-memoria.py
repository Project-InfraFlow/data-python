import psutil
import time
import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    'user': os.getenv("USER_DB"),
    'password': os.getenv("PASSWORD_DB"),
    'host': os.getenv("HOST_DB"),
    'database': os.getenv("DATABASE_DB")
}

def executar_query(query, params=None):
    try:
        with mysql.connector.connect(**config) as db:
            with db.cursor() as cursor:
                cursor.execute(query, params)
                if query.strip().lower().startswith('select'):
                    return cursor.fetchall()
                db.commit()
                return cursor.lastrowid
    except Exception as e:
        print(f'❌ Erro: {e}')
        return None

def corrigir_problemas():
    print("🔧 Corrigindo problemas identificados...")
    
    id_maquina = 1
    
    # 1. CRIAR COMPONENTE PROCESSOS (se não existir)
    processos_componente = executar_query(
        "SELECT id_componente FROM componente WHERE nome_componente = 'Processos' AND fk_id_maquina = %s",
        (id_maquina,)
    )
    
    if not processos_componente:
        print("📝 Criando componente Processos...")
        executar_query(
            "INSERT INTO componente (fk_id_maquina, nome_componente, unidade_de_medida) VALUES (%s, %s, %s)",
            (id_maquina, 'Processos', 'qtd')
        )
        print("✅ Componente Processos criado")
    else:
        print("✅ Componente Processos já existe")
    
    # 2. CRIAR ALERTAS PARA LEITURAS EXISTENTES >84%
    print("📊 Verificando leituras sem alertas...")
    leituras_sem_alerta = executar_query("""
        SELECT l.id_leitura, l.dados_float, l.data_hora_captura
        FROM leitura l
        JOIN componente c ON c.id_componente = l.fk_id_componente
        WHERE c.nome_componente = 'RAM'
        AND l.dados_float > 84
        AND l.id_leitura NOT IN (
            SELECT fk_id_leitura FROM alerta
        )
        ORDER BY l.data_hora_captura DESC
        LIMIT 10
    """)
    
    if leituras_sem_alerta:
        print(f"🚨 Encontradas {len(leituras_sem_alerta)} leituras críticas sem alerta")
        
        for leitura in leituras_sem_alerta:
            id_leitura = leitura[0]
            uso_percent = leitura[1]
            data_hora = leitura[2]
            
            # Buscar ID do componente RAM
            id_componente_ram = executar_query(
                "SELECT id_componente FROM componente WHERE nome_componente = 'RAM' AND fk_id_maquina = %s",
                (id_maquina,)
            )[0][0]
            
            # Determinar tipo de alerta
            if uso_percent > 84:
                id_parametro = 4  # Crítico
                descricao = f'Uso CRÍTICO de memória: {uso_percent}%'
                print(f"🔴 Criando alerta crítico para leitura {id_leitura}: {uso_percent}%")
            else:
                id_parametro = 3  # Alta utilização  
                descricao = f'Alta utilização de memória: {uso_percent}%'
                print(f"🟡 Criando alerta de alta utilização para leitura {id_leitura}: {uso_percent}%")
            
            # Inserir alerta
            executar_query(
                "INSERT INTO alerta (fk_id_leitura, fk_id_componente, fk_parametro_alerta, descricao, status_alerta) VALUES (%s, %s, %s, %s, %s)",
                (id_leitura, id_componente_ram, id_parametro, descricao, 1)
            )
        
        print("✅ Alertas criados para leituras existentes")
    else:
        print("✅ Todas as leituras críticas já têm alertas")
    
    # 3. GERAR LEITURA DE PROCESSOS DE TESTE
    print("🖥️ Gerando leitura de processos...")
    id_componente_processos = executar_query(
        "SELECT id_componente FROM componente WHERE nome_componente = 'Processos' AND fk_id_maquina = %s",
        (id_maquina,)
    )[0][0]
    
    total_processos = len(psutil.pids())
    executar_query(
        "INSERT INTO leitura (fk_id_componente, fk_id_maquina, dados_float, data_hora_captura) VALUES (%s, %s, %s, %s)",
        (id_componente_processos, id_maquina, total_processos, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    print(f"✅ Leitura de processos gerada: {total_processos} processos")
    
    print("🎯 Correções aplicadas com sucesso!")

if __name__ == "__main__":
    corrigir_problemas()