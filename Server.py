import socket
import sys

# import thread module
from _thread import *
import threading

from message_server import MessageServer


# thread function

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    connected  = True
    while connected:
        msg = conn.recv(1024)
        message = MessageServer(msg, addr[1]) #pass the message and port its coming from
        message.read()
        if not msg:
            print(f"[CLOSING CONNECTION] {addr} disconnected!")
            break

        message.write()
        conn.send(message.send_response)
    
    conn.close()


def main():
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

    server.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()

# code referenced from https://www.geeksforgeeks.org/socket-programming-multi-threading-python/