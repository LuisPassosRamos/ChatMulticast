import os
import json
import threading
import socket
import time
import random

PORT = 50007
MULTICAST_GROUP = "224.1.1.1"
SERVER_ID = "server"

REPLICA_SERVER_FILE = os.path.join(os.getcwd(), "replica_server.json")
CHECKPOINT_SERVER_FILE = os.path.join(os.getcwd(), "checkpoint_server.json")

NEIGHBORS = set()  # Set of client UUIDs
LOCK = threading.Lock()
token_holder = SERVER_ID  # Initially, server holds the token

def inicializar_arquivos():
    """Cria os arquivos de réplica e checkpoint do servidor na raíz, se não existirem."""
    if not os.path.exists(REPLICA_SERVER_FILE):
        with open(REPLICA_SERVER_FILE, "w") as f:
            json.dump([], f, indent=4)
        print("[LOG] Arquivo de réplica do servidor criado em:", REPLICA_SERVER_FILE)
    if not os.path.exists(CHECKPOINT_SERVER_FILE):
        with open(CHECKPOINT_SERVER_FILE, "w") as f:
            # Server checkpoint: token=True means server holds token
            json.dump({"last_message": "", "token": True, "neighbors": []}, f, indent=4)
        print("[LOG] Arquivo de checkpoint do servidor criado em:", CHECKPOINT_SERVER_FILE)

def salvar_checkpoint(last_msg, token, neighbors):
    """Salva o estado atual no checkpoint do servidor."""
    with LOCK:
        estado = {"last_message": last_msg, "token": token, "neighbors": sorted(list(neighbors))}
        with open(CHECKPOINT_SERVER_FILE, "w") as f:
            json.dump(estado, f, indent=4)
        print("[LOG] Checkpoint do servidor salvo:", estado)

def gravar_mensagem(msg_obj):
    """Grava uma mensagem no arquivo de réplica do servidor."""
    with LOCK:
        try:
            with open(REPLICA_SERVER_FILE, "r") as f:
                historico = json.load(f)
        except Exception:
            historico = []
        historico.append(msg_obj)
        with open(REPLICA_SERVER_FILE, "w") as f:
            json.dump(historico, f, indent=4)
        print("[LOG] Mensagem gravada na réplica do servidor:", msg_obj)

def enviar_token(sock):
    """Se houver clientes, passa o token para o primeiro deles; caso contrário, mantém-o no servidor."""
    global token_holder
    with LOCK:
        if NEIGHBORS:
            next_node = sorted(list(NEIGHBORS))[0]
            token_holder = next_node
            token_msg = {"type": "token", "next": next_node, "sender": SERVER_ID}
            sock.sendto(json.dumps(token_msg).encode(), (MULTICAST_GROUP, PORT))
            salvar_checkpoint("Token passado for " + next_node, False, NEIGHBORS)
            print(f"[LOG] {SERVER_ID}: Token enviado para {next_node}.")
        else:
            token_holder = SERVER_ID
            salvar_checkpoint("Sem cliente", True, NEIGHBORS)
            print(f"[LOG] {SERVER_ID}: Sem cliente conectado. Token permanece.")

def processar_mensagens():
    """Processa mensagens recebidas: join, chat and token."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", PORT))
    sock.setsockopt(socket.IPPROTO_IP,
                    socket.IP_MULTICAST_TTL, 2)
    sock.setsockopt(socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0"))
    while True:
        data, addr = sock.recvfrom(4096)
        try:
            msg = json.loads(data.decode())
            print(f"[LOG] Servidor recebeu de {addr}: {msg}")
        except json.JSONDecodeError:
            print("[ERRO] Falha ao decodificar mensagem.")
            continue

        msg_type = msg.get("type")
        sender = msg.get("sender")

        if msg_type == "join":
            with LOCK:
                NEIGHBORS.add(sender)
            salvar_checkpoint("Join de " + sender, token_holder == SERVER_ID, NEIGHBORS)
            # Enviar lista atualizada de vizinhos para todos.
            neighbors_msg = {"type": "neighbors", "neighbors": sorted(list(NEIGHBORS))}
            sock.sendto(json.dumps(neighbors_msg).encode(), (MULTICAST_GROUP, PORT))
            print(f"[LOG] Novo nó {sender} entrou. Neighbors: {sorted(list(NEIGHBORS))}")
            if token_holder == SERVER_ID:
                enviar_token(sock)

        elif msg_type == "chat":
            content = msg.get("content", "")
            gravar_mensagem({"type": "chat", "content": content, "sender": sender})
            salvar_checkpoint("Chat: " + content, token_holder == SERVER_ID, NEIGHBORS)
            print(f"[LOG] Mensagem de {sender}: {content}")
            # Retransmite a mensagem para todos (multicast)
            time.sleep(random.uniform(0.1, 1.0))
            sock.sendto(data, (MULTICAST_GROUP, PORT))

        elif msg_type == "token":
            # Se o token retorna ao servidor (next==server), passa para o próximo cliente
            if msg.get("next") == SERVER_ID:
                print(f"[LOG] {SERVER_ID}: Token retornou.")
                enviar_token(sock)
            # Otherwise, assume the token is handled by the client.
        # Additional types (ex. sync) can be handled here.

def reconciliar_replicas():
    """Periodicamente sincroniza a réplica do servidor (aqui envia uma mensagem de sync)."""
    while True:
        time.sleep(10)
        with LOCK:
            try:
                with open(REPLICA_SERVER_FILE, "r") as f:
                    historico = json.load(f)
            except Exception:
                historico = []
        sync_msg = {"type": "sync", "history": historico}
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_sock.sendto(json.dumps(sync_msg).encode(), (MULTICAST_GROUP, PORT))
        print("[LOG] Réplicas sincronizadas.")

if __name__ == "__main__":
    inicializar_arquivos()
    threading.Thread(target=processar_mensagens, daemon=True).start()
    threading.Thread(target=reconciliar_replicas, daemon=True).start()
    print("[LOG] Servidor iniciado. Aguardando mensagens...")
    while True:
        time.sleep(1)
