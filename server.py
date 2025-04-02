# Importa as bibliotecas necessárias
import socket
import json
import os
import threading
import time  # Para delay artificial
import random  # Para delay artificial

# Configurações de multicast e porta
MULTICAST_GROUP = "224.1.1.1"
PORT = 50007
REPLICA_SERVER_FILE = "replica_server.json"
CHECKPOINT_SERVER_FILE = "checkpoint_server.json"

NEIGHBORS = set()

# Locks para sincronização dos arquivos
replica_lock = threading.Lock()
checkpoint_lock = threading.Lock()

def inicializar_arquivo_servidor():
    """Inicializa os arquivos de réplica e checkpoint do servidor."""
    if not os.path.exists(REPLICA_SERVER_FILE):
        with open(REPLICA_SERVER_FILE, "w") as f:
            json.dump([], f, indent=4)
    if not os.path.exists(CHECKPOINT_SERVER_FILE):
        estado_inicial = {"last_message": "", "neighbors": []}
        with open(CHECKPOINT_SERVER_FILE, "w") as f:
            json.dump(estado_inicial, f, indent=4)

def salvar_checkpoint_servidor(last_message, neighbors):
    """Salva o estado atual no checkpoint do servidor."""
    with checkpoint_lock:
        estado = {"last_message": last_message, "neighbors": sorted(list(neighbors))}
        with open(CHECKPOINT_SERVER_FILE, "w") as f:
            json.dump(estado, f, indent=4)

def gravar_mensagem_servidor(mensagem_obj):
    """Grava uma mensagem (incluindo 'content' e 'sender') no arquivo do servidor."""
    with replica_lock:
        with open(REPLICA_SERVER_FILE, "r") as f:
            historico = json.load(f)
        historico.append(mensagem_obj)
        with open(REPLICA_SERVER_FILE, "w") as f:
            json.dump(historico, f, indent=4)

def processar_mensagens(msg_queue):
    """
    Processa mensagens recebidas (obtidas da fila compartilhada).
    Opera os seguintes tipos:
      - "join": adiciona novo nó e envia lista de neighbors via um socket de envio.
      - "token": repassa o token (evita reenvio se já encaminhado).
      - "chat": grava a mensagem, atualiza checkpoint e reenvia.
    """
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Servidor esperando mensagens (filtradas pela fila)...")
    while True:
        msg_text, addr = msg_queue.get()  # bloqueia até ter mensagem
        try:
            msg_obj = json.loads(msg_text)
        except json.JSONDecodeError:
            continue
        msg_type = msg_obj.get("type", "chat")
        sender = msg_obj.get("sender", "unknown")
        if msg_type == "ping":
            # Responder com pong se desejar (não utilizado neste exemplo)
            continue
        if msg_type == "join":
            NEIGHBORS.add(sender)
            salvar_checkpoint_servidor(f"Join de {sender}", NEIGHBORS)
            # Envia a lista completa de neighbors para todos
            neighbors_msg = {"type": "neighbors", "neighbors": sorted(list(NEIGHBORS))}
            send_sock.sendto(json.dumps(neighbors_msg).encode(), (MULTICAST_GROUP, PORT))
            print(f"Novo nó {sender} entrou. Neighbors: {sorted(list(NEIGHBORS))}")
            continue
        if msg_type == "token":
            if msg_obj.get("forwarded", False):
                continue
            msg_obj["forwarded"] = True
            gravar_mensagem_servidor(msg_obj)
            salvar_checkpoint_servidor(f"Token enviado para {msg_obj.get('next')}", NEIGHBORS)
            print(f"Token recebido de {addr} - repassado: {json.dumps(msg_obj)}")
            send_sock.sendto(json.dumps(msg_obj).encode(), (MULTICAST_GROUP, PORT))
            continue
        if msg_type == "chat":
            content = msg_obj.get("content", "")
            time.sleep(random.uniform(0.1, 1.0))
            log_entry = {"type": "chat", "content": content, "sender": sender}
            gravar_mensagem_servidor(log_entry)
            salvar_checkpoint_servidor(content, NEIGHBORS)
            print(f"Mensagem recebida de {addr} - Sender: {sender} - Content: {content}")
            send_sock.sendto(msg_text.encode(), (MULTICAST_GROUP, PORT))

if __name__ == "__main__":
    inicializar_arquivo_servidor()
    # A função processar_mensagens agora espera uma fila de mensagens como parâmetro.
    # A inicialização da fila e o fornecimento de mensagens devem ser feitos externamente.
