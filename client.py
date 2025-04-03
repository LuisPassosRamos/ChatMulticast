import os
import json
import threading
import socket
import time
import random
import uuid

PORT = 50007
MULTICAST_GROUP = "224.1.1.1"
SERVER_ADDR = (MULTICAST_GROUP, PORT)
CLIENT_UUID = uuid.uuid4().hex[:8]

REPLICA_FILE = os.path.join(os.getcwd(), f"replica_{CLIENT_UUID}.json")
CHECKPOINT_FILE = os.path.join(os.getcwd(), f"checkpoint_{CLIENT_UUID}.json")

checkpoint_lock = threading.Lock()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", PORT))
sock.setsockopt(socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0"))

def inicializar_arquivos():
    """Cria os arquivos de réplica e checkpoint do cliente na raíz, se não existirem."""
    if not os.path.exists(REPLICA_FILE):
        with open(REPLICA_FILE, "w") as f:
            json.dump([], f, indent=4)
        print(f"[LOG] {CLIENT_UUID}: Arquivo de réplica criado em {REPLICA_FILE}")
    if not os.path.exists(CHECKPOINT_FILE):
        with checkpoint_lock, open(CHECKPOINT_FILE, "w") as f:
            json.dump({"last_message": "", "token": False, "neighbors": []}, f, indent=4)
        print(f"[LOG] {CLIENT_UUID}: Arquivo de checkpoint criado em {CHECKPOINT_FILE}")

def salvar_checkpoint(last_msg, token, neighbors):
    """Salva o estado atual no checkpoint do cliente."""
    estado = {"last_message": last_msg, "token": token, "neighbors": neighbors}
    with checkpoint_lock, open(CHECKPOINT_FILE, "w") as f:
        json.dump(estado, f, indent=4)
    print(f"[LOG] {CLIENT_UUID}: Checkpoint salvo: {estado}")

def carregar_checkpoint():
    """Carrega o estado salvo no checkpoint, tratando erros."""
    with checkpoint_lock:
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            salvar_checkpoint("", False, [])
            return {"last_message": "", "token": False, "neighbors": []}

def gravar_mensagem(msg_obj):
    """Grava uma mensagem (chat ou token) na réplica do cliente."""
    try:
        with open(REPLICA_FILE, "r") as f:
            historico = json.load(f)
    except Exception:
        historico = []
    historico.append(msg_obj)
    with open(REPLICA_FILE, "w") as f:
        json.dump(historico, f, indent=4)
    print(f"[LOG] {CLIENT_UUID}: Mensagem gravada: {msg_obj}")

def enviar_join():
    """Envia mensagem de join para o servidor."""
    join_msg = {"type": "join", "sender": CLIENT_UUID}
    sock.sendto(json.dumps(join_msg).encode(), SERVER_ADDR)
    print(f"[LOG] {CLIENT_UUID}: Join enviado.")

def calcular_proximo_vizinho(neighbors):
    """Calcula o próximo nó no anel lógico usando a ordem alfabética."""
    if CLIENT_UUID not in neighbors:
        neighbors.append(CLIENT_UUID)
    vizinhos = sorted(neighbors)
    idx = vizinhos.index(CLIENT_UUID)
    return vizinhos[(idx + 1) % len(vizinhos)]

def enviar_mensagem_automatica():
    """Envia uma mensagem automática para o servidor ao receber o token."""
    mensagem = f"Mensagem automática de {CLIENT_UUID}"
    msg_obj = {"type": "chat", "content": mensagem, "sender": CLIENT_UUID}
    sock.sendto(json.dumps(msg_obj).encode(), SERVER_ADDR)
    gravar_mensagem(msg_obj)
    print(f"[LOG] {CLIENT_UUID}: Mensagem automática enviada.")

def receber_mensagens():
    """Processa as mensagens recebidas do servidor."""
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            msg = json.loads(data.decode())
            msg_type = msg.get("type", "chat")
            
            if msg_type == "neighbors":
                neighbors = msg.get("neighbors", [])
                checkpoint = carregar_checkpoint()
                salvar_checkpoint(checkpoint["last_message"], checkpoint["token"], neighbors)
                print(f"[LOG] {CLIENT_UUID}: Neighbors atualizados: {neighbors}")

            elif msg_type == "token":
                # Se a mensagem de token é direcionada a este cliente
                if msg.get("next") == CLIENT_UUID:
                    print(f"[LOG] {CLIENT_UUID}: Token recebido.")
                    # Ao receber token, envia automáticamente sua mensagem
                    enviar_mensagem_automatica()
                    # Atualiza checkpoint e calcula o próximo nó do anel
                    checkpoint = carregar_checkpoint()
                    proximo = calcular_proximo_vizinho(checkpoint["neighbors"])
                    token_msg = {"type": "token", "next": proximo, "sender": CLIENT_UUID}
                    time.sleep(random.uniform(0.1, 1.0))
                    sock.sendto(json.dumps(token_msg).encode(), SERVER_ADDR)
                    print(f"[LOG] {CLIENT_UUID}: Token enviado para {proximo}.")

            elif msg_type == "chat":
                content = msg.get("content", "")
                sender = msg.get("sender", "unknown")
                print(f"[LOG] {CLIENT_UUID}: Mensagem recebida de {sender}: '{content}'")
                gravar_mensagem(msg)
            elif msg_type == "sync":
                # Opcional: processar mensagem de sincronização se desejar
                pass

        except json.JSONDecodeError:
            continue

if __name__ == "__main__":
    print(f"[LOG] Cliente iniciado com ID: {CLIENT_UUID}")
    inicializar_arquivos()
    enviar_join()
    time.sleep(3)
    checkpoint = carregar_checkpoint()
    # Se ainda não houver neighbors, o client torna-se dono do token para iniciar o anel
    if not checkpoint["neighbors"] or (checkpoint["neighbors"] == [CLIENT_UUID]):
        salvar_checkpoint("", True, [CLIENT_UUID])
        print(f"[LOG] {CLIENT_UUID}: Nenhum neighbor ou único. Token concedido a mim.")
    threading.Thread(target=receber_mensagens, daemon=True).start()
    # Aqui, o envio de mensagens é acionado automaticamente ao receber token
    while True:
        time.sleep(1)
