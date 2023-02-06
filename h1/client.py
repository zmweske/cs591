# Zach Weske
# CS 591, Spring 2023
# Homework 1
#   client component

""" Usage: 
    python client.py
    - runs with default SERVER_ADDR:SERVER_PORT and 
      will continue to ask for files to retrieve until
      "quit" or "^D" (ctrl+d) is sent
    
    python client.py [ADDRESS] [PORT]
    - same as above but with specified ADDRESS:PORT

    python client.py [ADDRESS] [PORT] [FILE]
    - attempts to retrieve FILE from ADDRESS:PORT once and exits
"""

import socket
import time
import argparse
import uuid

SERVER_ADDR = "localhost"
SERVER_PORT = 8888
USER = str(uuid.uuid4())


def connection(chat, port):
    if chat == "QUIT":
        return None

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_ADDR, port))
        client_socket.send((chat).encode())
        data = client_socket.recv(1024).decode()
        client_socket.close()
        return(data)
    except Exception as e:
        print("Client error: " + type(e).__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--address", action="store", dest="SERVER_ADDR", default=SERVER_ADDR)
    parser.add_argument("-p", "--port",    action="store", dest="SERVER_PORT", default=SERVER_PORT)
    parser.add_argument("-u", "--user", "--uuid", action="store", dest="USER", default=USER)
    args = parser.parse_args()
    
    SERVER_ADDR = args.SERVER_ADDR
    SERVER_PORT = int(args.SERVER_PORT)
    USER = args.USER

    # print(SERVER_ADDR, SERVER_PORT, USER)
    # try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_ADDR, SERVER_PORT))
    client_socket.send(b"CONNECT " + USER.encode())
    # client_socket.send(("GET " + page + " HTTP/1.0").encode())
    new_port = int(client_socket.recv(1024).decode())
    client_socket.close()
    print("Attempting to begin new connection on port", new_port)

    stop = False
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # client_socket.setblocking(0)
    time.sleep(0.2)
    client_socket.connect((SERVER_ADDR, new_port))
    while not stop:
        # while (chat := input("> ")) == '':
        #     # print("please send a chat...")
        #     pass
        try:
            chat = input("> ")
        except EOFError as e:
            chat = '\x04'
        if chat.strip() == "":
            continue
        # TODO make input non blocking
        client_socket.send((chat).encode())
        data = client_socket.recv(1024).decode()
        print({True: "No data received", False: data}[data == None])
        if chat == '\x04' or chat == "QUIT":
            stop = True
            print("Exiting client...")
            continue
    client_socket.close()
    # except Exception as e:
    #     print("Client error: " + type(e).__name__)


    # data = None
    # stop = False
    # while not stop:
    #     if len(sys.argv) != 4:
    #         page = input("\nEnter a localhost:8888 page to view: ")
    #         if page == '\x04' or page == "quit":
    #             stop = True
    #             print("Exiting client...")
    #             continue
    #     else:
    #         page = sys.argv[3]
    #         stop = True
    #     data = connection(page)
    #     print({True: "No data received", False: data}[data == None])



    
