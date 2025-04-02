import socket
import threading
import subprocess
import time
import json
import random
from queue import Queue

# Cria o socket de recepção multicast compartilhado (único bind na porta 50007)
MULTICAST_GROUP = "224.1.1.1"
PORT = 50007

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

# Funções para iniciar a lógica do servidor e do cliente
def iniciar_servidor():
    # Importa a função modificada do servidor (que usa a fila)
    from server import inicializar_arquivo_servidor, processar_mensagens
    inicializar_arquivo_servidor()
    processar_mensagens(queue_server)

def iniciar_cliente():
    # Importa a função modificada do cliente (que usa a fila)
    from client import inicializar_arquivos, enviar_join, receber_mensagens, enviar_mensagens, carregar_checkpoint, salvar_checkpoint
    inicializar_arquivos()
    enviar_join()
    time.sleep(3)
    checkpoint = carregar_checkpoint()
    if not checkpoint["neighbors"] or (checkpoint["neighbors"] == [] or checkpoint["neighbors"] == [checkpoint.get("CLIENT_UUID", "")]):
        salvar_checkpoint("", True, [checkpoint.get("CLIENT_UUID", "")])
        print("Nenhum neighbor definido ou sou o único. Token concedido a mim.")
    # Inicia as threads de recebimento e envio do cliente
    thread_receber = threading.Thread(target=receber_mensagens, args=(queue_client,), daemon=True)
    thread_receber.start()
    thread_enviar = threading.Thread(target=enviar_mensagens, daemon=True)
    thread_enviar.start()
    thread_receber.join()
    thread_enviar.join()

if __name__ == "__main__":
    # Inicia a thread que recebe do socket multicast compartilhado
    thread_receiver = threading.Thread(target=receiver, daemon=True)
    thread_receiver.start()
    
    # Inicia as threads do servidor e do cliente
    thread_server = threading.Thread(target=iniciar_servidor, daemon=True)
    thread_client = threading.Thread(target=iniciar_cliente, daemon=True)
    thread_server.start()
    # Pequeno atraso para permitir que o servidor inicie
    time.sleep(1)
    thread_client.start()
    
    thread_server.join()
    thread_client.join()