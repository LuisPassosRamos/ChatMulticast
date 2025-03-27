import socket

MULTICAST_GROUP = "224.1.1.1"
PORT = 5007

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

while True:
    msg = input("Digite sua mensagem: ")
    sock.sendto(msg.encode(), (MULTICAST_GROUP, PORT))
