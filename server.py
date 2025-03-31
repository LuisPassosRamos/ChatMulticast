# Importa a biblioteca socket do Python para trabalhar com sockets
import socket, json, os, time

# Define o endereço de multicast e a porta
MULTICAST_GROUP = "224.1.1.1"
PORT = 5007

"""
Cria um socket UDP e o associa ao endereço e porta definidos.
sock é o objeto que representa o socket, socket é o módulo e socket() é o construtor da classe socket.
AF_INET: Define que o socket será do tipo IPv4
SOCK_DGRAM: Define que o socket será do tipo UDP
Poderia ser usado mais protocolos, mas para o nosso caso, o UDP é o mais adequado.
"""
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

'''
Associa o socket ao endereço e porta definidos.
.bind() é um método do objeto socket que associa o socket a um endereço e porta.
O primeiro argumento é o endereço, que no caso é uma string vazia, indicando que o socket pode receber mensagens de qualquer endereço.
O segundo argumento é a porta.
'''
sock.bind(("", PORT))


'''
Adiciona ao grupo multicast
.setsockopt() é um método do objeto socket que define opções para o socket.
O primeiro argumento é o protocolo, que no caso é o IP.
O segundo argumento é a opção, opção é um valor que define o comportamento do socket.
Nesse caso, a opção é IP_ADD_MEMBERSHIP, que define que o socket será adicionado a um grupo multicast.
O terceiro argumento é o valor da opção.
.inet_aton() é uma função do módulo socket que converte um endereço IP em um número inteiro de 32 bits.
O endereço IP do grupo multicast é passado como argumento.
"0.0.0.0" é o endereço do host.
Para adicionar um socket a um grupo multicast, é necessário definir a opção IP_ADD_MEMBERSHIP.
O valor dessa opção é a união do endereço do grupo multicast e o endereço do host.
'''
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0"))

# Cria ou carrega o arquivo de réplicas
if not os.path.exists("replica_server.json"):
    with open("replica_server.json", "w") as f:
        json.dump([], f)

"""
Função para gravar mensagem em formato JSON,
adicionando cada mensagem em uma lista no arquivo replica_server.json
"""
def gravar_mensagem_servidor(mensagem):
    with open("replica_server.json", "r") as f:
        historico = json.load(f)
    historico.append(mensagem)
    with open("replica_server.json", "w") as f:
        json.dump(historico, f)

# Printa uma mensagem informando que o servidor está esperando mensagens
print("Servidor esperando mensagens...")

'''
Loop infinito para receber mensagens.
Enquanto o servidor estiver rodando, ele vai receber mensagens.
data é a mensagem recebida, addr é o endereço do remetente.
.recvfrom() é um método do objeto socket que recebe uma mensagem (lembrando, socket é o módulo e sock é o objeto).
O argumento é o tamanho máximo da mensagem.
A mensagem é decodificada de bytes para string.
{addr} é o endereço do remetente, data.decode() é a mensagem recebida.
No python, colocar entre chaves {} uma variável dentro de uma string, é chamado de f-string.
O : indica que o que vem a seguir é um formato. Nesse caso, o formato é o método decode() da variável data.
'''
while True:
    data, addr = sock.recvfrom(1024)
    msg = data.decode()
    gravar_mensagem_servidor(msg)
    print(f"Mensagem recebida de {addr}: {msg}")
