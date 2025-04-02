import socket
import json
import os
import threading
import time  # Adicionado no início do arquivo
import logging

# Configuração do logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configurações de multicast
MULTICAST_GROUP = "224.1.1.1"
PORT = 50007
REPLICA_FILE = "replica.json"
CHECKPOINT_FILE = "checkpoint.json"

clock_local = 0
name_client = "Cliente A"

# Configuração do socket para comunicação multicast
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", PORT))
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 5)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0"))

# Lock para sincronização de acesso ao arquivo de réplicas
replica_lock = threading.Lock()


def inicializar_arquivos():
    """Inicializa os arquivos necessários para o cliente."""
    global clock_local
    if not os.path.exists(REPLICA_FILE):
        with open(REPLICA_FILE, "w") as f:
            json.dump([], f)

    if not os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump({"last_message": "", "token": True, "neighbors": [], "clock": clock_local}, f)
    else:
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
            clock_local = data.get("clock", 0)


def gravar_mensagem(mensagem):
    """Grava uma mensagem no arquivo de réplicas."""
    try:
        with replica_lock:
            with open(REPLICA_FILE, "r") as f:
                historico = json.load(f)
                historico.append(mensagem)
            with open(REPLICA_FILE, "w") as f:
                json.dump(historico, f, indent=4)
        logging.info(f"Mensagem gravada: {mensagem}")
    except (FileNotFoundError, json.JSONDecodeError):
        logging.error("Erro ao acessar o arquivo de réplicas. Criando um novo arquivo.")
        with open(REPLICA_FILE, "w") as f:
            json.dump([mensagem], f, indent=4)


def salvar_checkpoint(last_msg, token, neighbors, clock):
    """Salva o estado atual no arquivo de checkpoint."""
    checkpoint_data = {
        "last_message": last_msg,
        "token": token,
        "neighbors": neighbors,
        "clock": clock
    }
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint_data, f)


def carregar_checkpoint():
    """Carrega o estado salvo no arquivo de checkpoint."""
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Erro ao carregar o checkpoint. Restaurando estado inicial.")
        salvar_checkpoint(last_msg="", token=True, neighbors=[], clock=0)
        return {"last_message": "", "token": True, "neighbors": [], "clock":0}


def sincronizar_replicas():
    """Sincroniza as mensagens recebidas fora de ordem."""
    with replica_lock:
        with open(REPLICA_FILE, "r") as f:
            historico = json.load(f)
        historico = sorted(historico)
        with open(REPLICA_FILE, "w") as f:
            json.dump(historico, f)


def verificar_servidor():
    """Verifica se o servidor está ativo."""
    global name_client
    global clock_local
    try:
        msg = {
            "mensagem": "ping",
            "clock": clock_local,
            "remetente": name_client
        }
        msg_json = json.dumps(msg)
        sock.sendto(msg_json.encode(), (MULTICAST_GROUP, PORT))
        sock.settimeout(2)
        data, addr = sock.recvfrom(1024)
        if data.decode() == "pong":
            print("Servidor ativo.")
            return True
    except socket.timeout:
        print("Servidor não encontrado. Verifique se ele está ativo.")
        return False


def receber_mensagens():
    """Recebe mensagens do grupo multicast."""
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            msg_completa = json.loads(data.decode())
            msg = msg_completa["mensagem"]
            clock = msg_completa["clock"]
            remetente = msg_completa["remetente"]
            global clock_local
            clock_local = max(clock_local, clock) + 1

            gravar_mensagem(msg)
            sincronizar_replicas()
            print(f"Mensagem recebida de {remetente}: {msg}")

            # Simula a liberação do token após receber uma mensagem
            checkpoint = carregar_checkpoint()
            if not checkpoint["token"]:
                salvar_checkpoint(last_msg=checkpoint["last_message"], token=True, neighbors=checkpoint["neighbors"])
                print("Token recebido após mensagem.")
        except socket.timeout:
            time.sleep(1)  # Aguarda 1 segundo antes de tentar novamente
            continue


def enviar_mensagens():
    """Envia mensagens para o grupo multicast."""
    while True:
        global clock_local
        global name_client
        checkpoint = carregar_checkpoint()
        if not checkpoint["token"]:
            print("Aguardando o token para enviar mensagens...")
            time.sleep(1)
            continue

        try:
            msg = input("Digite sua mensagem (ou 'exit' para sair): ").strip()
            if not msg or len(msg) > 256:
                print("Mensagem inválida. Tente novamente.")
                continue

            if msg.lower() == "exit":
                print("Encerrando o cliente...")
                salvar_checkpoint(last_msg="", token=False, neighbors=[], clock=clock_local)
                exit()

            clock_local += 1

            msg_completa = {
                "mensagem": msg,
                "clock": clock_local,
                "remetente": name_client
            }

            msg_json = json.dumps(msg_completa)
            # Envia a mensagem para o grupo multicast
            sock.sendto(msg_json.encode(), (MULTICAST_GROUP, PORT))
            gravar_mensagem(msg_completa)

            # Atualiza o checkpoint e libera o token
            salvar_checkpoint(last_msg=msg, token=False, neighbors=[], clock=clock_local)
            print("Mensagem enviada. Token liberado.")

            # Simula a passagem do token para outro cliente
            print("Passando o token para o próximo cliente...")
            time.sleep(2)
            salvar_checkpoint(last_msg=msg, token=True, neighbors=checkpoint["neighbors"], clock=clock_local)
        except EOFError:
            print("\nEntrada finalizada. Encerrando o cliente...")
            salvar_checkpoint(last_msg="", token=False, neighbors=[], clock=clock_local)
            exit()


if __name__ == "__main__":
    print("Tentando se conectar ao servidor...")
    inicializar_arquivos()
    if not verificar_servidor():
        print("Servidor não está ativo. Por favor, inicie o servidor antes de executar o cliente.")
        exit()

    # Inicia threads para envio e recebimento de mensagens
    thread_receber = threading.Thread(target=receber_mensagens, daemon=True)
    thread_receber.start()

    thread_enviar = threading.Thread(target=enviar_mensagens, daemon=True)
    thread_enviar.start()

    # Mantém o cliente ativo
    thread_receber.join()
    thread_enviar.join()