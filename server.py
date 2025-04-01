# Importa as bibliotecas necessárias
import socket
import json
import os
import threading

# Configurações de multicast
MULTICAST_GROUP = "224.1.1.1"
PORT = 50007
REPLICA_SERVER_FILE = "replica_server.json"

# Configuração do socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", PORT))
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0"))

# Lock para sincronização de acesso ao arquivo de réplicas
replica_lock = threading.Lock()


def inicializar_arquivo_servidor():
    """Inicializa o arquivo de réplicas do servidor."""
    if not os.path.exists(REPLICA_SERVER_FILE):
        with open(REPLICA_SERVER_FILE, "w") as f:
            json.dump([], f)


def gravar_mensagem_servidor(mensagem):
    """Grava uma mensagem no arquivo de réplicas do servidor."""
    with replica_lock:
        with open(REPLICA_SERVER_FILE, "r") as f:
            historico = json.load(f)
        historico.append(mensagem)
        with open(REPLICA_SERVER_FILE, "w") as f:
            json.dump(historico, f)


def processar_mensagens():
    """Processa mensagens recebidas pelo servidor."""
    print("Servidor esperando mensagens...")
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            if data.decode().lower() == "exit":
                print("Encerrando o servidor...")
                break
            msg = data.decode()
            if msg == "ping":
                sock.sendto(b"pong", addr)
            gravar_mensagem_servidor(msg)
            print(f"Mensagem recebida de {addr}: {msg}")
    except KeyboardInterrupt:
        print("Servidor encerrado manualmente.")
    finally:
        sock.close()


if __name__ == "__main__":
    inicializar_arquivo_servidor()
    processar_mensagens()
