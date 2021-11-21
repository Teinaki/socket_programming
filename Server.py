import socket
import struct
import json
import io

# import thread module
from _thread import *
import threading

from message_server import MessageServer

print_lock = threading.Lock()

# thread function

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    connected  = True
    while connected:
        msg = conn.recv(1024)
        print(msg)
        message = MessageServer(msg)
        message.read()
        if not msg:
            print('Bye')
            break
    
    conn.close()


def Main():
    host = "127.0.0.1"
    port = 65432
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    print("Socket binded to port", port)

    # put the socket into listening mode

    # a forever loop until client wants to exit
    server.listen()
    print(f"[LISTENING] Socket is listening on {host}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")

    s.close()


if __name__ == '__main__':
    Main()

# code referenced from https://www.geeksforgeeks.org/socket-programming-multi-threading-python/
