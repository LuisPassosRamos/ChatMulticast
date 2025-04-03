import os
import json
import threading
import socket
import time
import random
import uuid

# Configurações de rede
PORT = 50007
MULTICAST_GROUP = "224.1.1.1"
SERVER_ADDR = (MULTICAST_GROUP, PORT)
CLIENT_UUID = uuid.uuid4().hex[:8]  # ID único para este cliente

# Caminhos para arquivos de persistência
REPLICA_FILE = os.path.join(os.getcwd(), f"replica_{CLIENT_UUID}.json")
CHECKPOINT_FILE = os.path.join(os.getcwd(), f"checkpoint_{CLIENT_UUID}.json")

# Controle de concorrência e estado
checkpoint_lock = threading.Lock()
replica_lock = threading.Lock()
teste_enviado = False  # Controle para envio único de mensagem de teste
pode_enviar_mensagem = False  # Controle para exclusão mútua (token ring)

# Configuração do socket para comunicação multicast
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", PORT))
sock.setsockopt(socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0"))


def inicializar_arquivos():
    """
    Cria os arquivos de réplica e checkpoint do cliente se não existirem.
    
    Este método garante a persistência dos dados e possibilita a recuperação
    em caso de falhas ou reinício do cliente.
    """
    if not os.path.exists(REPLICA_FILE):
        with open(REPLICA_FILE, "w") as f:
            json.dump([], f, indent=4)
        print(f"[LOG] {CLIENT_UUID}: Arquivo de réplica criado.")
    
    if not os.path.exists(CHECKPOINT_FILE):
        with checkpoint_lock, open(CHECKPOINT_FILE, "w") as f:
            json.dump({
                "last_message": "", 
                "token": False,  # Inicia sem o token
                "neighbors": []
            }, f, indent=4)
        print(f"[LOG] {CLIENT_UUID}: Arquivo de checkpoint criado.")


def salvar_checkpoint(last_msg, token, neighbors):
    """
    Salva o estado atual no checkpoint do cliente.
    
    Implementa tolerância a falhas salvando o estado atual do cliente,
    permitindo recuperação em caso de queda.
    
    Args:
        last_msg: String com a última mensagem processada
        token: Boolean indicando se o cliente possui o token
        neighbors: Lista de IDs dos vizinhos no anel lógico
    """
    estado = {"last_message": last_msg, "token": token, "neighbors": neighbors}
    with checkpoint_lock, open(CHECKPOINT_FILE, "w") as f:
        json.dump(estado, f, indent=4)
    print(f"[LOG] {CLIENT_UUID}: Checkpoint atualizado: token={token}, vizinhos={len(neighbors)}")


def carregar_checkpoint():
    """
    Carrega o estado salvo no checkpoint, tratando possíveis erros.
    
    Parte da estratégia de tolerância a falhas, permite recuperar
    o último estado conhecido do cliente.
    
    Returns:
        dict: Estado do cliente (token, vizinhos, última mensagem)
    """
    with checkpoint_lock:
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[LOG] {CLIENT_UUID}: Erro ao carregar checkpoint: {e}")
            # Cria um checkpoint padrão caso não exista ou esteja corrompido
            salvar_checkpoint("", False, [])
            return {"last_message": "", "token": False, "neighbors": []}


def sincronizar_replicas():
    """
    Ordena as mensagens na réplica local para garantir consistência.
    
    Implementação do princípio de consistência eventual, garantindo
    que as mensagens estejam em ordem cronológica.
    """
    try:
        with replica_lock:
            with open(REPLICA_FILE, "r") as f:
                historico = json.load(f)
            
            # Ordena mensagens por timestamp (se disponível)
            if historico and isinstance(historico[0], dict) and "timestamp" in historico[0]:
                historico = sorted(historico, key=lambda x: x.get("timestamp", 0))
            
            with open(REPLICA_FILE, "w") as f:
                json.dump(historico, f, indent=4)
    except Exception as e:
        print(f"[LOG] {CLIENT_UUID}: Erro ao sincronizar réplica: {e}")


def gravar_mensagem(msg_obj):
    """
    Grava uma mensagem na réplica local do cliente.
    
    Implementa o mecanismo de replicação, mantendo cópia local
    de todas as mensagens do chat.
    
    Args:
        msg_obj: Objeto de mensagem a ser armazenado
    """
    with replica_lock:
        try:
            with open(REPLICA_FILE, "r") as f:
                historico = json.load(f)
        except Exception as e:
            print(f"[LOG] {CLIENT_UUID}: Erro ao ler histórico: {e}")
            historico = []
        
        # Adiciona timestamp para ordenação posterior
        if isinstance(msg_obj, dict) and "timestamp" not in msg_obj:
            msg_obj["timestamp"] = time.time()
            
        historico.append(msg_obj)
        with open(REPLICA_FILE, "w") as f:
            json.dump(historico, f, indent=4)
        print(f"[LOG] {CLIENT_UUID}: Mensagem gravada: {msg_obj}")


def enviar_join():
    """
    Envia mensagem de join para o servidor para ingressar no anel lógico.
    
    Esta função implementa o processo de entrada no sistema distribuído,
    solicitando inclusão no anel lógico do Token Ring.
    """
    join_msg = {"type": "join", "sender": CLIENT_UUID}
    # Delay artificial para simular latência de rede
    time.sleep(random.uniform(0.1, 0.5))  
    sock.sendto(json.dumps(join_msg).encode(), SERVER_ADDR)
    print(f"[LOG] {CLIENT_UUID}: Join enviado. Aguardando token...")


def calcular_proximo_vizinho(neighbors):
    """
    Calcula o próximo nó no anel lógico usando a ordem alfabética.
    
    Implementação crucial do algoritmo Token Ring, determina para 
    qual nó o token deve ser passado.
    
    Args:
        neighbors: Lista de IDs dos vizinhos
        
    Returns:
        str: ID do próximo nó no anel
    """
    if CLIENT_UUID not in neighbors:
        neighbors.append(CLIENT_UUID)
    vizinhos = sorted(neighbors)
    idx = vizinhos.index(CLIENT_UUID)
    return vizinhos[(idx + 1) % len(vizinhos)]


def enviar_mensagem_automatica():
    """
    Envia uma mensagem automática quando o cliente possui o token.
    
    Demonstra o funcionamento da exclusão mútua via Token Ring,
    enviando mensagem apenas quando possui o token.
    """
    global teste_enviado, pode_enviar_mensagem
    
    if not pode_enviar_mensagem:
        print(f"[LOG] {CLIENT_UUID}: Tentativa de envio sem ter o token!")
        return
    
    if not teste_enviado:
        print(f"[LOG] {CLIENT_UUID}: Iniciando acesso à seção crítica.")
        # Delay artificial para simular latência e processamento
        time.sleep(random.uniform(0.1, 1.0))  
        
        mensagem = f"Teste de mensagem de {CLIENT_UUID}"
        msg_obj = {
            "type": "chat", 
            "content": mensagem, 
            "sender": CLIENT_UUID,
            "timestamp": time.time()
        }
        sock.sendto(json.dumps(msg_obj).encode(), SERVER_ADDR)
        gravar_mensagem(msg_obj)
        print(f"[LOG] {CLIENT_UUID}: Mensagem automática de teste enviada.")
        teste_enviado = True
        print(f"[LOG] {CLIENT_UUID}: Seção crítica finalizada.")
    else:
        print(f"[LOG] {CLIENT_UUID}: Teste já enviado, ignorando envio.")


def passar_token():
    """
    Implementa a passagem do token para o próximo nó no anel lógico.
    
    Esta função é parte central do algoritmo Token Ring, garantindo
    a exclusão mútua distribuída no sistema.
    """
    global pode_enviar_mensagem
    checkpoint = carregar_checkpoint()
    neighbors = checkpoint["neighbors"]
    
    # Se tiver vizinhos além de si mesmo
    if len(neighbors) > 1:
        proximo = calcular_proximo_vizinho(neighbors)
        token_msg = {"type": "token", "next": proximo, "sender": CLIENT_UUID}
        
        # Marca que o cliente não possui mais o token e atualiza checkpoint
        salvar_checkpoint(checkpoint["last_message"], False, neighbors)
        # Delay artificial para estabilidade da rede
        time.sleep(random.uniform(0.1, 0.3))  
        
        sock.sendto(json.dumps(token_msg).encode(), SERVER_ADDR)
        print(f"[LOG] {CLIENT_UUID}: Token enviado para {proximo}.")
        pode_enviar_mensagem = False
    else:
        # Se for o único cliente, retorna o token ao servidor
        token_msg = {"type": "token", "next": "server", "sender": CLIENT_UUID}
        salvar_checkpoint(checkpoint["last_message"], False, neighbors)
        sock.sendto(json.dumps(token_msg).encode(), SERVER_ADDR)
        print(f"[LOG] {CLIENT_UUID}: Token retornado para o servidor.")
        pode_enviar_mensagem = False


def receber_mensagens():
    """
    Processa continuamente as mensagens recebidas do servidor.
    
    Esta função implementa o loop principal de processamento de mensagens,
    tratando diferentes tipos (token, neighbors, chat, sync).
    """
    global pode_enviar_mensagem
    
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            # Delay artificial para simular variação de latência
            time.sleep(random.uniform(0.05, 0.2))  
            
            msg = json.loads(data.decode())
            msg_type = msg.get("type", "chat")
            
            if msg_type == "neighbors":
                # Atualização da lista de vizinhos (anel lógico)
                neighbors = msg.get("neighbors", [])
                if CLIENT_UUID not in neighbors:
                    neighbors.append(CLIENT_UUID)
                
                checkpoint = carregar_checkpoint()
                old_token = checkpoint["token"]
                
                salvar_checkpoint(checkpoint["last_message"], old_token, neighbors)
                print(f"[LOG] {CLIENT_UUID}: Neighbors atualizados: {neighbors}")
                
            elif msg_type == "token":
                # Recebimento do token - exclusão mútua distribuída
                if msg.get("next") == CLIENT_UUID:
                    print(f"[LOG] {CLIENT_UUID}: Token recebido.")
                    checkpoint = carregar_checkpoint()
                    salvar_checkpoint(checkpoint["last_message"], True, checkpoint["neighbors"])
                    
                    # Agora pode enviar mensagens (seção crítica)
                    pode_enviar_mensagem = True
                    
                    # Executa a seção crítica (envio de mensagem)
                    enviar_mensagem_automatica()
                    
                    # Libera a seção crítica e passa o token adiante
                    passar_token()

            elif msg_type == "chat":
                # Mensagem de chat - adiciona ao histórico local
                content = msg.get("content", "")
                sender = msg.get("sender", "unknown")
                print(f"[LOG] {CLIENT_UUID}: Mensagem recebida de {sender}: '{content}'")
                gravar_mensagem(msg)
                
            elif msg_type == "sync":
                # Sincronização periódica (consistência eventual)
                history = msg.get("history", [])
                if history:
                    print(f"[LOG] {CLIENT_UUID}: Recebendo sincronização com {len(history)} mensagens.")
                    with replica_lock:
                        with open(REPLICA_FILE, "r") as f:
                            local_history = json.load(f)
                        
                        # Combina históricos eliminando duplicações
                        combined = local_history.copy()
                        for msg in history:
                            if msg not in combined:
                                combined.append(msg)
                        
                        with open(REPLICA_FILE, "w") as f:
                            json.dump(combined, f, indent=4)
                    
                    print(f"[LOG] {CLIENT_UUID}: Réplica sincronizada.")
                    sincronizar_replicas()

        except json.JSONDecodeError as e:
            print(f"[LOG] {CLIENT_UUID}: Erro ao decodificar mensagem: {e}")
            continue
        except Exception as e:
            print(f"[LOG] {CLIENT_UUID}: Erro ao processar mensagem: {e}")


if __name__ == "__main__":
    print(f"[LOG] Cliente iniciado com ID: {CLIENT_UUID}")
    inicializar_arquivos()
    
    # Inicia sem o token (aguarda receber do servidor)
    salvar_checkpoint("", False, [])
    
    # Solicita ingresso no anel lógico
    enviar_join()
    
    # Thread para processamento contínuo de mensagens
    threading.Thread(target=receber_mensagens, daemon=True).start()
    
    # Thread para sincronização periódica (consistência eventual)
    def sincronizar_periodicamente():
        """Thread dedicada à sincronização periódica da réplica local."""
        while True:
            time.sleep(30)  # A cada 30 segundos
            sincronizar_replicas()
    
    threading.Thread(target=sincronizar_periodicamente, daemon=True).start()
    
    # Main thread mantém o cliente em execução
    while True:
        time.sleep(1)
