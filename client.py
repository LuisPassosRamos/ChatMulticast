# Importa a biblioteca socket do Python para trabalhar com sockets
import socket
import time
import random
import json, os

# Define o endereço de multicast e a porta
MULTICAST_GROUP = "224.1.1.1"
PORT = 5007

"""
Cria um socket UDP para envio de mensagens.
.setsockopt() define o TTL do multicast.
"""
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

# Cria ou carrega o arquivo de réplicas
if not os.path.exists("replica.json"):
    with open("replica.json", "w") as f:
        json.dump([], f)

# Cria ou carrega o arquivo de checkpoints
if not os.path.exists("checkpoint.json"):
    with open("checkpoint.json", "w") as f:
        json.dump({"last_message": "", "token": False, "neighbors": []}, f)

"""
Função para gravar a mensagem no arquivo replica.json
Cada mensagem é armazenada em formato JSON, mantendo histórico de envio
"""
def gravar_mensagem(mensagem):
    with open("replica.json", "r") as f:
        historico = json.load(f)
    historico.append(mensagem)
    with open("replica.json", "w") as f:
        json.dump(historico, f)

"""
Função para salvar checkpoint, incluindo última mensagem,
token (para Token Ring) e lista de vizinhos para exclusão mútua
"""
def salvar_checkpoint(last_msg, token, neighbors):
    checkpoint_data = {
        "last_message": last_msg,
        "token": token,
        "neighbors": neighbors
    }
    with open("checkpoint.json", "w") as f:
        json.dump(checkpoint_data, f)

"""
Função para carregar checkpoint (caso precisemos fazer rollback)
Retorna as informações relevantes para retomar estado
"""
def carregar_checkpoint():
    with open("checkpoint.json", "r") as f:
        return json.load(f)

"""
Exemplo simples de distribuição de token (Token Ring).
O 'neighbors' é uma lista de endereços IP/port do próximo cliente no anel.
Se este cliente tiver 'token' True, ele pode enviar mensagens.
Depois de enviar, pode repassar o token ao próximo nó do anel.
Esta é uma versão bem simplificada que assume rede estável.
"""
def enviar_token():
    cp = carregar_checkpoint()
    if cp["neighbors"]:
        next_neighbor = cp["neighbors"][0]  # Exemplo: envia sempre ao primeiro da lista
        # Convertemos 'next_neighbor' num (ip, port) e enviamos uma string "TOKEN"
        ip, port = next_neighbor.split(":")
        sock.sendto("TOKEN".encode(), (ip, int(port)))
        cp["token"] = False
        salvar_checkpoint(cp["last_message"], cp["token"], cp["neighbors"])

"""
Loop principal: se tem token, pode enviar mensagens;
caso não tenha, fica escutando token via recvfrom.
"""
cp = carregar_checkpoint()

# Caso precisemos restaurar algo
print("Carregando checkpoint: ", cp)

# Se neighbours estiver vazio, este nó é "único" ou inicial no anel: assume token
if not cp["neighbors"]:
    cp["token"] = True
    salvar_checkpoint(cp["last_message"], cp["token"], cp["neighbors"])

# Loop infinito de envio/recebimento
while True:
    # Se o cliente não tem token, espera receber o token
    if not cp["token"]:
        sock.settimeout(None)  # Bloqueia até receber
        data, addr = sock.recvfrom(1024)
        # Se a mensagem for 'TOKEN', assume token
        msg = data.decode()
        if msg == "TOKEN":
            cp["token"] = True
            salvar_checkpoint(cp["last_message"], cp["token"], cp["neighbors"])

    # Se tem token, pode enviar mensagem
    if cp["token"]:
        msg = input("Digite sua mensagem: ")
        # Simula atraso de 1 a 3 segundos
        time.sleep(random.uniform(1, 3))

        # Envia ao grupo multicast
        sock.sendto(msg.encode(), (MULTICAST_GROUP, PORT))

        # Grava em réplica e atualiza checkpoint
        gravar_mensagem(msg)
        cp["last_message"] = msg
        salvar_checkpoint(cp["last_message"], cp["token"], cp["neighbors"])

        # Após enviar, repassa token
        enviar_token()
    else:
        # Em caso de backups periódicos ou algo do gênero
        time.sleep(1)
