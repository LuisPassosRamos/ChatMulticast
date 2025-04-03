import socket
import threading
import subprocess
import time
import json
import random
import re
from queue import Queue
from collections import deque
from datetime import datetime
import os

# Configurações de multicast
MULTICAST_GROUP = "224.1.1.1"
PORT = 50007

# Configuração do buffer de logs
log_buffer = deque(maxlen=1000)
last_output_time = time.time()
log_lock = threading.Lock()

# Configuração para filtrar mensagens repetitivas
LOG_COOLDOWN = 0.5  # tempo mínimo entre logs similares (em segundos)
recent_logs = {}  # armazenar logs recentes por tipo para evitar duplicação


def derrubar_servicos():
    """Derruba os serviços do Docker Compose, se estiverem rodando."""
    print("[LOG] Derrubando serviços...")
    try:
        subprocess.run(["docker-compose", "down"], check=True)
        print("[LOG] Serviços derrubados.")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao derrubar os serviços: {e}")


def iniciar_docker_compose():
    """Inicia os serviços do Docker Compose no modo desanexado."""
    print("[LOG] Iniciando Docker Compose...")
    try:
        subprocess.run(["docker-compose", "up", "--build", "-d"], check=True)
        print("[LOG] Serviços iniciados.")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao iniciar os serviços: {e}")


def limpar_terminal():
    """Limpa o terminal para uma melhor visualização."""
    os.system('cls' if os.name == 'nt' else 'clear')


def formatar_log(servico, mensagem):
    """
    Formata uma mensagem de log para exibição organizada.
    
    Args:
        servico: Nome do serviço (container) que gerou o log
        mensagem: Conteúdo da mensagem de log
        
    Returns:
        String formatada com timestamp e cores
    """
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # Extrai o ID do cliente do formato "[LOG] XXXX: mensagem"
    id_match = re.search(r'\[LOG\] ([a-zA-Z0-9]+):', mensagem)
    client_id = id_match.group(1) if id_match else ""
    
    # Formata com cores ANSI (verde para servidor, azul para clientes)
    prefix = f"\033[32m[{timestamp}] {servico:<12}\033[0m" if 'server' in servico else f"\033[34m[{timestamp}] {servico:<12}\033[0m"
    
    # Formata objetos JSON de forma mais compacta
    if 'Checkpoint' in mensagem and '{' in mensagem:
        try:
            json_start = mensagem.find('{')
            if json_start >= 0:
                before = mensagem[:json_start].strip()
                json_obj = json.loads(mensagem[json_start:])
                json_formatted = json.dumps(json_obj, sort_keys=True)
                mensagem = f"{before} {json_formatted}"
        except:
            pass  # Se falhar, mantém a mensagem original
    
    return f"{prefix}: {mensagem}"


def deve_exibir_log(servico, mensagem):
    """
    Determina se um log deve ser exibido, evitando mensagens duplicadas.
    
    Args:
        servico: Nome do serviço que gerou o log
        mensagem: Conteúdo da mensagem
        
    Returns:
        Boolean indicando se o log deve ser exibido
    """
    global recent_logs
    
    # Evita mensagens repetidas de join
    if "Join enviado" in mensagem:
        key = f"{servico}_join"
        if key in recent_logs and time.time() - recent_logs[key] < LOG_COOLDOWN:
            return False
        recent_logs[key] = time.time()
        return True
    
    # Exibe todas as outras mensagens
    return True


def processar_buffer_logs():
    """
    Processa o buffer de logs periodicamente para exibição organizada.
    Garante um intervalo mínimo entre mensagens para melhor leitura.
    """
    global last_output_time
    
    while True:
        time.sleep(0.1)
        with log_lock:
            # Permite um tempo entre as exibições de logs
            current_time = time.time()
            if log_buffer and current_time - last_output_time >= 0.2:  # 200ms entre logs
                mensagem = log_buffer.popleft()
                print(mensagem)
                last_output_time = current_time


def filtrar_e_formatar_linha(servico, linha):
    """
    Filtra e formata uma linha de log.
    
    Args:
        servico: Nome do serviço que gerou o log
        linha: Linha de log bruta
        
    Returns:
        String formatada ou None se a linha deve ser ignorada
    """
    linha = linha.strip()
    if not linha:
        return None
        
    # Ignora linhas sem informações úteis
    if linha.startswith('[') and ']' in linha and len(linha) < 10:
        return None
        
    # Verifica se deve exibir este log
    if deve_exibir_log(servico, linha):
        return formatar_log(servico, linha)
    
    return None


def acompanhar_logs(servico):
    """
    Acompanha os logs de um serviço Docker e os coloca no buffer para processamento.
    
    Args:
        servico: Nome do serviço Docker a ser monitorado
    """
    try:
        proc = subprocess.Popen(
            ["docker", "logs", "-f", servico],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        while True:
            linha = proc.stdout.readline()
            if not linha:
                break
                
            linha_formatada = filtrar_e_formatar_linha(servico, linha)
            if linha_formatada:
                with log_lock:
                    log_buffer.append(linha_formatada)
                    
        proc.wait()
    except Exception as e:
        with log_lock:
            log_buffer.append(f"\033[31m[ERRO] Falha ao acompanhar logs de {servico}: {e}\033[0m")


def acompanhar_todos_logs():
    """
    Cria threads para acompanhar os logs do servidor e de todos os clientes.
    Organiza a exibição dos logs de forma legível e cronológica.
    """
    print("\033[1m[LOG] Iniciando exibição de logs organizada...\033[0m")
    time.sleep(1)
    limpar_terminal()
    
    # Thread para processar e exibir logs do buffer
    thread_processor = threading.Thread(target=processar_buffer_logs)
    thread_processor.daemon = True
    thread_processor.start()
    
    # Threads para capturar logs
    threads = []
    
    # Adiciona o acompanhamento do servidor
    threads.append(threading.Thread(target=acompanhar_logs, args=("chat_server",)))
    
    # Adiciona o acompanhamento dos clientes
    for i in range(1, 6):  # 5 clientes conforme docker-compose
        threads.append(threading.Thread(target=acompanhar_logs, args=(f"chatmulticast-client-{i}",)))

    for thread in threads:
        thread.daemon = True
        thread.start()

    # Exibe status inicial
    print("\033[1;36m==== Sistema de Chat Multicast - Logs Organizados ====\033[0m")
    print("\033[37mPressione Ctrl+C para encerrar\033[0m\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\033[1;36m==== Encerrando exibição de logs ====\033[0m")


if __name__ == "__main__":
    try:
        # Passo 1: Derrubar serviços existentes
        derrubar_servicos()

        # Passo 2: Iniciar os serviços do Docker Compose
        iniciar_docker_compose()

        # Passo 3: Aguardar inicialização dos contêineres
        print("\n\033[33m[LOG] Aguardando inicialização dos serviços...\033[0m")
        time.sleep(5)

        # Passo 4: Acompanhar logs do servidor e dos clientes
        acompanhar_todos_logs()

    except Exception as e:
        print(f"\033[31m[ERRO] Ocorreu um erro inesperado: {e}\033[0m")