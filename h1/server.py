# Zach Weske
# CS 591, Spring 2023
# Homework 1
#   server component

""" Usage: 
    python server.py
    - runs simple server on localhost:SERVER_PORT

    # python server.py
"""

import socket
import sys
import threading
import queue
import argparse
import random
import time
import json
import logging
from collections import defaultdict

# FIXME log all print statements

SERVER_PORT = 8888
THREADS = queue.Queue()
MESSAGES = queue.Queue()  # send messages from threads to main to be broadcasted
ACTIVE_USERS = defaultdict(lambda: queue.Queue())  # send broadcasts back to threads

STOP_COMMAND = False
PORT_RANGE = [9001, 9999]


class connection_thread():
    def __init__(self, port, user, message_sender, incoming_messages):
        self.port = port
        self.user = user
        self.messages_broadcaster = message_sender
        self.incoming = incoming_messages
        self.outgoing = queue.Queue()
        self.stop = False

        logging.info("Starting client listener thread on port " + str(port))  # FIXME log all print statements
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("localhost", port))
        self.server_socket.listen(20)
        self.client_socket, addr = self.server_socket.accept()
        logging.info("User connect on port " + str(port) + ": " + self.user)
                
        self.broadcast_listener = threading.Thread(target=self.listen_to_broadcast)
        self.client_listener = threading.Thread(target=self.accept_message)
        self.client_sender = threading.Thread(target=self.send_to_client)
        
        self.client_listener.start()
        self.broadcast_listener.start()
        self.client_sender.start()


    def send_to_client(self):
        while not self.stop:
            to_send = self.outgoing.get()
            self.client_socket.sendall(to_send)
        
    def listen_to_broadcast(self):
        # print("listenening to broadcaster")
        while not self.stop:
            json_msg = self.incoming.get()
            # print("---\n", json_msg, "\n---")
            if json_msg["user"] == self.user:
                continue
            message = json_msg["user"] + ": " + json_msg["message"]
            # print("sending " + message + " to client: " + self.user)
            message = message.encode()
            self.outgoing.put(message)
            # self.client_socket.sendall(message)  # FIXME
            
    def accept_message(self):
        response = b""
        try:
            while not self.stop:
                try:
                    message = self.client_socket.recv(1024).decode()
                    try:
                        if message == "QUIT" or message == '\x04':
                            response = b"Closing server connection...goodbye!"
                            self.stop = True
                        elif message == "LIST":
                            response = ('\n'.join(list(ACTIVE_USERS.keys()))).encode()
                        else:
                            message = json.dumps({"user": self.user, "message": message})
                            message = message.encode()
                            self.messages_broadcaster.put(message)
                            response = b"echo:" + message
                    except Exception as e:
                        logging.error(" - Error: " + type(e).__name__ + str(e))

                    self.outgoing.put(response)
                    # self.client_socket.sendall(response)

                    # VERSION 1:
                    #   for byte in response:
                    #       client_socket.send(byte.to_bytes(1, "little"))
                    # VERSION 2:
                    #   client_socket.send(response)
                    # VERSION 3:
                    #   client_socket.sendall(response)

                except Exception as e:
                    logging.error("Error: " + type(e).__name__ + str(e))
                    break
            time.sleep(1)
            logging.info("Logging out user " + self.user)
            ACTIVE_USERS[self.user] = "QUIT"
            logging.info("Closing server connection " + str(self.port) + "...")
            self.client_socket.close()
        except Exception as e:
            logging.error("Error: " + type(e).__name__ + str(e))





def broadcast_listener():
    to_delete = queue.Queue()
    while not STOP_COMMAND:
        message = MESSAGES.get()
        json_msg = json.loads(message)
        logging.info(json_msg["user"] + ": " + json_msg["message"])
        
        for user in ACTIVE_USERS:
            if not isinstance(ACTIVE_USERS[user], queue.Queue):
                to_delete.put_nowait(user)
                continue
            if json_msg["user"] != user:
                ACTIVE_USERS[user].put_nowait(json_msg)
        while not to_delete.empty():
            user = to_delete.get_nowait()
            logging.info("user " + user + " logged out...")
            del ACTIVE_USERS[user]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", action="store", dest="SERVER_PORT", default=SERVER_PORT)
    args = parser.parse_args()
    SERVER_PORT = int(args.SERVER_PORT)

    # logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    logging.basicConfig(filename='h1/server.log', encoding='utf-8', 
                        level=logging.DEBUG, filemode='w',
                        format='%(asctime)s - %(levelname)-7s - %(message)s')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


    # Prepare initial sever socket
    logging.info("Starting server on port " +  str(SERVER_PORT))
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("localhost", SERVER_PORT))
    server_socket.listen(20)
    logging.info("Serving on localhost:" + str(SERVER_PORT))
    
    broadcast_listener_thread = threading.Thread(target=broadcast_listener)
    broadcast_listener_thread.start()
    THREADS.put_nowait(broadcast_listener_thread) 

    while not STOP_COMMAND:
        # accept/establish new connections in a new thread
        logging.info("Ready to accept new client on main thread...")
        client_socket, addr = server_socket.accept()
        if not (message := client_socket.recv(1024).decode()).startswith("CONNECT"):
            client_socket.close()
            continue
        user = message[8:]
        # ACTIVE_USERS[user] = True
        client_port = random.randrange(PORT_RANGE[0], PORT_RANGE[1])
        client_socket.send(str(client_port).encode())
        # client_socket.send(client_port)
        client_socket.close()
        new_thread = threading.Thread(target=connection_thread, args=(client_port,user,MESSAGES,ACTIVE_USERS[user]))
        new_thread.start()
        THREADS.put_nowait(new_thread)
        # new_thread.join()

    while not THREADS.empty():
        THREADS.get().join()
    server_socket.close()
    logging.info("Server stopped.")
    sys.exit()
