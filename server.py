import os
import json
import threading
import socket
import time
import random

# Configurações de rede
PORT = 50007
MULTICAST_GROUP = "224.1.1.1"
SERVER_ID = "server"

# Caminhos para arquivos de persistência
REPLICA_SERVER_FILE = os.path.join(os.getcwd(), "replica_server.json")
CHECKPOINT_SERVER_FILE = os.path.join(os.getcwd(), "checkpoint_server.json")

# Controle de estado e concorrência
NEIGHBORS = set()  # Conjunto de UUIDs dos clientes conectados
LOCK = threading.Lock()
token_holder = SERVER_ID  # Inicialmente, o servidor detém o token


def inicializar_arquivos():
    """
    Cria os arquivos de réplica e checkpoint do servidor se não existirem.
    
    Garante a persistência dos dados e possibilita a recuperação em caso de falhas.
    """
    if not os.path.exists(REPLICA_SERVER_FILE):
        with open(REPLICA_SERVER_FILE, "w") as f:
            json.dump([], f, indent=4)
        print("[LOG] Arquivo de réplica do servidor criado em:", REPLICA_SERVER_FILE)
    
    if not os.path.exists(CHECKPOINT_SERVER_FILE):
        with open(CHECKPOINT_SERVER_FILE, "w") as f:
            # Checkpoint inicial: servidor possui o token
            json.dump({
                "last_message": "", 
                "token": True, 
                "neighbors": []
            }, f, indent=4)
        print("[LOG] Arquivo de checkpoint do servidor criado em:", CHECKPOINT_SERVER_FILE)


def salvar_checkpoint(last_msg, token, neighbors):
    """
    Salva o estado atual no checkpoint do servidor.
    
    Implementa tolerância a falhas permitindo a recuperação em caso de queda.
    
    Args:
        last_msg: String com a última mensagem processada
        token: Boolean indicando se o servidor possui o token
        neighbors: Lista/conjunto de IDs dos clientes conectados
    """
    with LOCK:
        estado = {"last_message": last_msg, "token": token, "neighbors": sorted(list(neighbors))}
        with open(CHECKPOINT_SERVER_FILE, "w") as f:
            json.dump(estado, f, indent=4)
        print(f"[LOG] Checkpoint do servidor: token={token}, neighbors={len(neighbors)}")


def carregar_checkpoint():
    """
    Carrega o estado salvo no checkpoint do servidor.
    
    Parte da estratégia de tolerância a falhas, permite recuperar
    o último estado conhecido do servidor.
    
    Returns:
        dict: Estado do servidor (token, vizinhos, última mensagem)
    """
    try:
        with open(CHECKPOINT_SERVER_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[LOG] Erro ao carregar checkpoint: {e}")
        # Cria um checkpoint padrão caso não exista ou esteja corrompido
        default = {"last_message": "", "token": True, "neighbors": []}
        salvar_checkpoint("", True, [])
        return default


def gravar_mensagem(msg_obj):
    """
    Grava uma mensagem na réplica do servidor.
    
    Implementa o mecanismo de replicação, mantendo cópia local
    de todas as mensagens do chat.
    
    Args:
        msg_obj: Objeto de mensagem a ser armazenado
    """
    with LOCK:
        try:
            with open(REPLICA_SERVER_FILE, "r") as f:
                historico = json.load(f)
        except Exception as e:
            print(f"[LOG] Erro ao ler histórico de mensagens: {e}")
            historico = []
        
        historico.append(msg_obj)
        with open(REPLICA_SERVER_FILE, "w") as f:
            json.dump(historico, f, indent=4)
        print("[LOG] Mensagem gravada na réplica do servidor:", msg_obj)


def enviar_token(sock, target=None):
    """
    Passa o token para o próximo nó no anel lógico.
    
    Controla o início e a continuidade do algoritmo Token Ring,
    implementando a exclusão mútua distribuída.
    
    Args:
        sock: Socket para envio da mensagem
        target: ID específico do cliente para enviar o token (opcional)
        
    Returns:
        bool: Indica se o token foi passado com sucesso
    """
    global token_holder
    with LOCK:
        if not NEIGHBORS:
            # Se não há clientes conectados, o servidor mantém o token
            token_holder = SERVER_ID
            salvar_checkpoint("Sem clientes", True, NEIGHBORS)
            print(f"[LOG] {SERVER_ID}: Sem clientes conectados. Token permanece.")
            return False
        
        # Determina o próximo detentor do token
        if target and target in NEIGHBORS:
            next_node = target
        else:
            next_node = sorted(list(NEIGHBORS))[0]
        
        # Envia o token e atualiza o estado
        token_holder = next_node
        token_msg = {"type": "token", "next": next_node, "sender": SERVER_ID}
        sock.sendto(json.dumps(token_msg).encode(), (MULTICAST_GROUP, PORT))
        salvar_checkpoint(f"Token enviado para {next_node}", False, NEIGHBORS)
        print(f"[LOG] {SERVER_ID}: Token enviado para {next_node}.")
        return True


def processar_mensagens():
    """
    Processa continuamente as mensagens recebidas dos clientes.
    
    Esta função implementa o loop principal de processamento de mensagens,
    tratando diferentes tipos (join, chat, token).
    """
    # Configuração do socket para comunicação multicast
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", PORT))
    sock.setsockopt(socket.IPPROTO_IP,
                    socket.IP_MULTICAST_TTL, 2)
    sock.setsockopt(socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0"))
    
    global token_holder
    
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            msg = json.loads(data.decode())
            
            # Delay artificial para simular latência de rede
            time.sleep(random.uniform(0.05, 0.2))
            print(f"[LOG] Servidor recebeu de {addr}: {msg}")
            
            msg_type = msg.get("type")
            sender = msg.get("sender")

            if msg_type == "join":
                # Processamento de novo cliente ingressando no sistema
                is_new = False
                with LOCK:
                    if sender not in NEIGHBORS:
                        NEIGHBORS.add(sender)
                        is_new = True
                
                if is_new:
                    print(f"[LOG] Novo nó {sender} entrou. Total de neighbors: {len(NEIGHBORS)}")
                    checkpoint = carregar_checkpoint()
                    has_token = token_holder == SERVER_ID
                    salvar_checkpoint(f"Join de {sender}", has_token, NEIGHBORS)
                    
                    # Notifica todos sobre a atualização da topologia do anel
                    neighbors_msg = {"type": "neighbors", "neighbors": sorted(list(NEIGHBORS))}
                    sock.sendto(json.dumps(neighbors_msg).encode(), (MULTICAST_GROUP, PORT))
                    
                    # Se o servidor possui o token e este é o primeiro cliente, inicia o ciclo
                    if has_token and len(NEIGHBORS) == 1:
                        print(f"[LOG] {SERVER_ID}: Primeiro cliente conectado, iniciando Token Ring.")
                        enviar_token(sock, sender)

            elif msg_type == "chat":
                # Processamento de mensagens de chat
                content = msg.get("content", "")
                
                # Adiciona timestamp se não existir (para ordenação)
                if "timestamp" not in msg:
                    msg["timestamp"] = time.time()
                    
                gravar_mensagem(msg)
                salvar_checkpoint(f"Chat: {content}", token_holder == SERVER_ID, NEIGHBORS)
                print(f"[LOG] Mensagem de {sender}: {content}")
                
                # Retransmite para todos (implementação do multicast)
                # Delay para simular latência variável
                time.sleep(random.uniform(0.1, 1.0))  
                sock.sendto(json.dumps(msg).encode(), (MULTICAST_GROUP, PORT))

            elif msg_type == "token":
                # Processamento do token (algoritmo Token Ring)
                if msg.get("next") in [SERVER_ID, "server"]:
                    print(f"[LOG] {SERVER_ID}: Token retornou do cliente {sender}.")
                    # Atualiza o estado: servidor possui o token
                    token_holder = SERVER_ID
                    salvar_checkpoint("Token retornou", True, NEIGHBORS)
                    
                    # Aguarda um pouco e repassa o token para continuar o ciclo
                    time.sleep(0.5)
                    enviar_token(sock)
                
        except json.JSONDecodeError as e:
            print(f"[ERRO] Falha ao decodificar mensagem: {e}")
        except Exception as e:
            print(f"[ERRO] Erro ao processar mensagem: {e}")


def reconciliar_replicas():
    """
    Periodicamente sincroniza a réplica do servidor com os clientes.
    
    Implementação do mecanismo de consistência eventual, garantindo
    que todos os nós tenham eventualmente o mesmo conjunto de mensagens.
    """
    while True:
        try:
            # Intervalo entre sincronizações
            time.sleep(15)
            
            with LOCK:
                try:
                    # Lê o histórico atual
                    with open(REPLICA_SERVER_FILE, "r") as f:
                        historico = json.load(f)
                    
                    # Ordena as mensagens por timestamp (se disponível)
                    if historico and isinstance(historico[0], dict) and "timestamp" in historico[0]:
                        historico = sorted(historico, key=lambda x: x.get("timestamp", 0))
                        with open(REPLICA_SERVER_FILE, "w") as f:
                            json.dump(historico, f, indent=4)
                    
                except Exception as e:
                    print(f"[ERRO] Falha ao carregar réplica para sincronização: {e}")
                    historico = []
            
            # Envia o histórico completo para todos os clientes
            sync_msg = {"type": "sync", "history": historico}
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.sendto(json.dumps(sync_msg).encode(), (MULTICAST_GROUP, PORT))
            print(f"[LOG] Réplicas sincronizadas. Total de mensagens: {len(historico)}")
            
        except Exception as e:
            print(f"[ERRO] Falha na sincronização de réplicas: {e}")


if __name__ == "__main__":
    # Inicializa o ambiente
    inicializar_arquivos()
    
    # Garante que o servidor inicia com o token
    checkpoint = carregar_checkpoint()
    if not checkpoint.get("token", True):
        salvar_checkpoint("Reinicialização", True, checkpoint.get("neighbors", []))
    
    # Thread para processamento de mensagens
    mensagens_thread = threading.Thread(target=processar_mensagens, daemon=True)
    mensagens_thread.start()
    
    # Thread para sincronização periódica (consistência eventual)
    sync_thread = threading.Thread(target=reconciliar_replicas, daemon=True)
    sync_thread.start()
    
    print("[LOG] Servidor iniciado. Aguardando mensagens...")
    
    # Main thread mantém o servidor em execução
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[LOG] Encerrando servidor...")
