import socket
import json
import os
import threading
import time  # Para delay artificial
import random  # Para delay artificial
import uuid

# Gera um ID curto (8 caracteres em hexadecimal) para este cliente
CLIENT_UUID = uuid.uuid4().hex[:8]
SERVER_ADDR = ("127.0.0.1", 50007)  # Endereço do servidor

# Nomes dos arquivos de réplica e checkpoint deste cliente (incluindo o ID curto)
REPLICA_FILE = f"replica_{CLIENT_UUID}.json"
CHECKPOINT_FILE = f"checkpoint_{CLIENT_UUID}.json"

# Socket para enviar (para o servidor)
sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_send.bind(("", 0))  # Usa porta dinâmica

def inicializar_arquivos():
    """Inicializa os arquivos de réplica e checkpoint do cliente."""
    if not os.path.exists(REPLICA_FILE):
        with open(REPLICA_FILE, "w") as f:
            json.dump([], f, indent=4)
    if not os.path.exists(CHECKPOINT_FILE):
        estado_inicial = {"last_message": "", "token": False, "neighbors": []}
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(estado_inicial, f, indent=4)

def salvar_checkpoint(last_msg, token, neighbors):
    """Salva o estado atual no arquivo de checkpoint do cliente."""
    estado = {"last_message": last_msg, "token": token, "neighbors": neighbors}
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(estado, f, indent=4)

def carregar_checkpoint():
    """Carrega o estado salvo no arquivo de checkpoint."""
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    except:
        salvar_checkpoint("", False, [])
        return {"last_message": "", "token": False, "neighbors": []}

def gravar_mensagem(mensagem_obj):
    """Grava uma mensagem (chat ou token) na réplica do cliente."""
    with open(REPLICA_FILE, "r") as f:
        historico = json.load(f)
    historico.append(mensagem_obj)
    with open(REPLICA_FILE, "w") as f:
        json.dump(historico, f, indent=4)

def enviar_join():
    """Envia mensagem de join para o servidor."""
    join_msg = {"type": "join", "sender": CLIENT_UUID}
    sock_send.sendto(json.dumps(join_msg).encode(), SERVER_ADDR)

def calcular_proximo(neighbors):
    """Calcula o próximo nó no anel de token.
       Se o CLIENT_UUID não estiver na lista, ele é adicionado.
    """
    if CLIENT_UUID not in neighbors:
        neighbors.append(CLIENT_UUID)
    neighbors_sorted = sorted(neighbors)
    atual_index = neighbors_sorted.index(CLIENT_UUID)
    return neighbors_sorted[(atual_index + 1) % len(neighbors_sorted)]

def enviar_mensagens():
    """
    Captura entrada do usuário e, se possuir o token, envia a mensagem de chat para o servidor.
    Em seguida, envia o token para o próximo nó.
    """
    while True:
        checkpoint = carregar_checkpoint()
        if not checkpoint["token"]:
            time.sleep(1)
            continue
        try:
            msg = input("Digite sua mensagem (ou 'exit' para sair): ").strip()
            if not msg or len(msg) > 256:
                continue
            if msg.lower() == "exit":
                exit()
            mensagem_obj = {"type": "chat", "content": msg, "sender": CLIENT_UUID}
            time.sleep(random.uniform(0.1, 1.0))
            sock_send.sendto(json.dumps(mensagem_obj).encode(), SERVER_ADDR)
            gravar_mensagem(mensagem_obj)
            salvar_checkpoint(msg, False, checkpoint["neighbors"])
            print("Mensagem enviada. Passando o token...")
            proximo = calcular_proximo(checkpoint["neighbors"])
            token_msg = {"type": "token", "next": proximo, "sender": CLIENT_UUID}
            time.sleep(random.uniform(0.1, 1.0))
            sock_send.sendto(json.dumps(token_msg).encode(), SERVER_ADDR)
            gravar_mensagem(token_msg)
            salvar_checkpoint(msg, False, checkpoint["neighbors"])
        except EOFError:
            exit()

def receber_mensagens(msg_queue):
    """
    Processa mensagens recebidas a partir da fila compartilhada.
    Trata:
      - "neighbors": atualiza a lista de nós.
      - "token": se direcionado a este cliente, adquire o token.
      - "chat": exibe a mensagem e registra na réplica.
    """
    while True:
        msg_text, addr = msg_queue.get()
        try:
            msg_obj = json.loads(msg_text)
        except json.JSONDecodeError:
            continue
        msg_type = msg_obj.get("type", "chat")
        if msg_type == "neighbors":
            neighbors = msg_obj.get("neighbors", [])
            checkpoint = carregar_checkpoint()
            salvar_checkpoint(checkpoint["last_message"], checkpoint["token"], neighbors)
            print(f"Neighbors atualizados: {neighbors}")
        elif msg_type == "token":
            if msg_obj.get("next") == CLIENT_UUID:
                checkpoint = carregar_checkpoint()
                salvar_checkpoint(checkpoint["last_message"], True, checkpoint["neighbors"])
                print("Token recebido. Agora você pode enviar mensagens.")
            gravar_mensagem(msg_obj)
        elif msg_type == "chat":
            content = msg_obj.get("content", "")
            sender = msg_obj.get("sender", "unknown")
            print(f"Mensagem recebida: {content} (from {sender})")
            gravar_mensagem(msg_obj)
        elif msg_type == "ping":
            continue

if __name__ == "__main__":
    print(f"Cliente iniciado com ID: {CLIENT_UUID}")
    inicializar_arquivos()
    enviar_join()
    time.sleep(3)
    checkpoint = carregar_checkpoint()
    if not checkpoint["neighbors"] or (checkpoint["neighbors"] == [CLIENT_UUID]):
        salvar_checkpoint("", True, [CLIENT_UUID])
        print("Nenhum neighbor definido ou sou o único. Token concedido a mim.")
    msg_queue = queue.Queue()
    thread_receber = threading.Thread(target=receber_mensagens, args=(msg_queue,), daemon=True)
    thread_receber.start()
    thread_enviar = threading.Thread(target=enviar_mensagens, daemon=True)
    thread_enviar.start()
    thread_receber.join()
    thread_enviar.join()
