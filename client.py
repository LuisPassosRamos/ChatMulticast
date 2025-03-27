# Importa a biblioteca socket do Python para trabalhar com sockets
import socket

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
"""
Adiciona ao grupo multicast
.setsockopt() é um método do objeto socket que define opções para o socket.
Opções são valores que definem o comportamento do socket.
O primeiro argumento é o protocolo, que no caso é o IP.
O segundo argumento é a opção, que no caso é o TTL do multicast.
TTL é o número de roteadores que a mensagem pode passar antes de ser descartada.
O terceiro argumento é o valor da opção, que no caso é 2. Ou seja, a mensagem pode passar por 2 roteadores antes de ser descartada.
"""
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

"""
Loop infinito para enviar mensagens.
Enquanto o cliente estiver rodando, ele vai enviar mensagens.
"""
while True:
    # Pede para o usuário digitar uma mensagem e armazena na variável msg
    msg = input("Digite sua mensagem: ")
    """
    Envia a mensagem para o grupo multicast.
    .sendto() é um método do objeto socket que envia uma mensagem para um endereço.
    O primeiro argumento é a mensagem, que é convertida para bytes. 
    Precisa ser convertida para bytes porque o socket só envia bytes.
    .encode() é um método da classe string que converte a string para bytes. Como default o encode() usa o encoding UTF-8.
    O segundo argumento é o endereço e porta. O endereço é o endereço do grupo multicast e a porta é a porta do grupo multicast.
    """
    sock.sendto(msg.encode(), (MULTICAST_GROUP, PORT))
