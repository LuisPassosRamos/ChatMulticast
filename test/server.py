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
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
            try:
                msg_completa = json.loads(data.decode())
                msg = msg_completa["mensagem"]
                clock = msg_completa["clock"]
                remetente = msg_completa["remetente"]

                if msg == "ping":
                    sock.sendto(b"pong", addr)
                    continue         
                
                msg_format_save = "Mensagem: " + msg + " | Clock: " + str(clock) + " | Remetente: " + remetente
                gravar_mensagem_servidor(msg_format_save)
                print("Mensagem recebida de " + remetente + " : " + msg)
            except json.JSONDecodeError:
                print("Não foi possível decodificar a mensagem recebida")        
    except KeyboardInterrupt:
        print("Servidor encerrado manualmente.")
    finally:
        sock.close()


if __name__ == "__main__":
    inicializar_arquivo_servidor()
    processar_mensagens()
