import socket
import threading
import subprocess
import time
import json
import random
from queue import Queue

# Configurações de multicast
MULTICAST_GROUP = "224.1.1.1"
PORT = 50007

# Configuração do socket multicast
shared_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
shared_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
shared_sock.bind(("0.0.0.0", PORT))
shared_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
shared_sock.setsockopt(
    socket.IPPROTO_IP,
    socket.IP_ADD_MEMBERSHIP,
    socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0")
)
shared_sock.settimeout(5)

# Duas filas para distribuir as mensagens: uma para o servidor, outra para o cliente.
queue_server = Queue()
queue_client = Queue()

def derrubar_servicos():
    """Derruba os serviços do Docker Compose, se estiverem rodando."""
    print("[LOG] Derrubando serviços...")
    try:
        subprocess.run(["docker-compose", "down"], check=True)
        print("[LOG] Serviços derrubados.")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao derrubar os serviços: {e}")

def receiver():
    """Thread que recebe dados do socket compartilhado e coloca em ambas as filas."""
    while True:
        try:
            data, addr = shared_sock.recvfrom(4096)
            msg = data.decode()
            # Distribui a mensagem para ambos os módulos (servidor e cliente)
            queue_server.put((msg, addr))
            queue_client.put((msg, addr))
        except socket.timeout:
            continue

def iniciar_docker_compose():
    """Inicia os serviços do Docker Compose no modo desanexado."""
    print("[LOG] Iniciando Docker Compose...")
    try:
        subprocess.run(["docker-compose", "up", "--build", "-d"], check=True)
        print("[LOG] Serviços iniciados.")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao iniciar os serviços: {e}")

def acompanhar_logs(servico):
    """Acompanha os logs de um serviço Docker e os imprime em tempo real."""
    print(f"[LOG] Acompanhando logs: {servico}")
    try:
        proc = subprocess.Popen(
            ["docker", "logs", "-f", servico],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Capture output line by line and print it.
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            print(f"[{servico}] {line.strip()}")
        proc.wait()
    except KeyboardInterrupt:
        print(f"[LOG] Interrompido o acompanhamento de logs do serviço: {servico}")
    except Exception as e:
        print(f"[ERRO] Falha ao acompanhar os logs do serviço {servico}: {e}")

def acompanhar_todos_logs():
    """Cria threads para acompanhar os logs do servidor e de todos os clientes."""
    print("[LOG] Acompanhando logs do servidor e dos clientes...")
    threads = []

    # Adiciona o acompanhamento do servidor
    threads.append(threading.Thread(target=acompanhar_logs, args=("chat_server",)))

    # Adiciona o acompanhamento dos clientes
    for i in range(1, 6):  # Ajuste o número de clientes conforme necessário
        threads.append(threading.Thread(target=acompanhar_logs, args=(f"chatmulticast-client-{i}",)))

    for thread in threads:
        thread.daemon = True  # Permite que o programa encerre se o main thread for interrompido.
        thread.start()

    # Mantenha o main thread ativo para que os logs continuem sendo exibidos
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[LOG] Interrupção pelo usuário.")

if __name__ == "__main__":
    try:
        # Passo 1: Derrubar serviços existentes
        derrubar_servicos()

        # Passo 2: Iniciar os serviços do Docker Compose
        iniciar_docker_compose()

        # Pequeno atraso para garantir que os contêineres estejam prontos
        time.sleep(5)

        # Passo 3: Acompanhar logs do servidor e dos clientes
        acompanhar_todos_logs()

    except Exception as e:
        print(f"[ERRO] Ocorreu um erro inesperado: {e}")