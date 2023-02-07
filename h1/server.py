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

SERVER_PORT = 8888
THREADS = queue.Queue()
MESSAGES = queue.Queue()  # send messages from threads to main to be broadcasted
ACTIVE_USERS = defaultdict(lambda: queue.Queue())  # send broadcasts back to threads
ACTIVE_USERNAMES = {}
LOGGING_OUT = queue.Queue()

STOP_COMMAND = False
PORT_RANGE = [9001, 9999]


# the thread spawned when a new client connects to the server
class connection_thread():
    def __init__(self, port, uuid, user, message_sender, incoming_messages):
        self.port = port
        self.user = user
        self.uuid = uuid
        self.messages_broadcaster = message_sender
        self.incoming = incoming_messages
        self.outgoing = queue.Queue()
        self.stop = False

        logging.info("Starting client listener thread on port " + str(self.port))
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("localhost", port))
        self.server_socket.listen(20)
        self.client_socket, addr = self.server_socket.accept()
        logging.info("User connect on port " + str(self.port) + ": " + self.uuid + 
                     {False: "(" + user + ")", True: "(without username)"}[user==uuid])

        # spawn threads
        self.broadcast_listener = threading.Thread(target=self.listen_to_broadcast)
        self.client_listener = threading.Thread(target=self.accept_message)
        self.client_sender = threading.Thread(target=self.send_to_client)
        
        self.client_listener.start()
        self.broadcast_listener.start()
        self.client_sender.start()
        
        self.client_listener.join()
        self.stop = True
        self.broadcast_listener.join()
        try:  # client socket may already be closed, but this will prevent a blocking client thread
            self.client_socket.send(b' ')
        except BrokenPipeError as e:
            pass
        self.client_sender.join()
        logging.info("Logging out user " + self.uuid + {False: "(" + self.user + ")", True: ""}[self.user==self.uuid])
        self.messages_broadcaster.put(json.dumps({"user": self.user, "uuid": self.uuid, "action": "QUIT", "message": "Logged out"}))
        LOGGING_OUT.put(self.uuid)
        logging.info("Closing server connection " + str(self.port) + "...")
        self.client_socket.close()

    # used to monitor all outgoing messages and send them over the socket back to the client
    def send_to_client(self):
        while not self.stop:
            to_send = self.outgoing.get()
            if self.stop:
                continue
            try:
                self.client_socket.sendall(to_send)
            except BrokenPipeError as e:
                self.stop = True
            except Exception as e:
                logging.warning("80: " + type(e).__name__ + ' ' + str(e))
    
    # a listens to the messages coming from other users (rebroadcasted by the server) or server messages
    def listen_to_broadcast(self):
        while not self.stop:
            json_msg = self.incoming.get()
            if self.stop:
                continue
            if json_msg["uuid"] == self.uuid:
                continue
            message = json_msg["user"] + {False:": ",True:" "}[json_msg["action"]=="CONNECT"] + json_msg["message"]
            message = message.encode()
            self.outgoing.put(message)
    
    # the primary running thread for this class
    def accept_message(self):
        try:
            while not self.stop:
                response = b""
                try:
                    message = self.client_socket.recv(1024).decode()
                    try:  # TODO convert to check action?
                        if message == "QUIT" or message == '\x04':
                            response = b"Closing server connection...goodbye!"
                            message = json.dumps({"user": self.user, "uuid": self.uuid, "action": "QUIT", "message": "Logged off"})
                            message = message.encode()
                            self.messages_broadcaster.put(message)
                            self.stop = True
                        elif message == "LIST":
                            # response = ('\n'.join(map(lambda u: u[u.find(':')+1:], list(ACTIVE_USERS.keys())))).encode()
                            response = ("Logged in users: " + ", ".join(list(ACTIVE_USERNAMES.values()))).encode()
                            self.outgoing.put(response)
                        elif message != "":  # 
                            message = json.dumps({"user": self.user, "uuid": self.uuid, "action": "message", "message": message})
                            message = message.encode()
                            self.messages_broadcaster.put(message)
                            # self.outgoing.put(b"echo:" + message)  # only used for server to client echo
                    except BrokenPipeError as e:  # catch garbage collected queue or closed socket (user logged out)
                        self.stop = True
                    except Exception as e:
                        logging.error("118: " + type(e).__name__ + ' ' + str(e))

                except Exception as e:
                    logging.error("124: " + type(e).__name__ + ' ' + str(e))
                    break
            time.sleep(1)  # used to allow everything to settle before shutting down server thread
            self.stop = True
            # unblock other threads waiting on queue.Queue.get()
            self.incoming.put(" ")
            self.outgoing.put(" ")
        except Exception as e:
            logging.error("130: " + type(e).__name__ + ' ' + str(e))




# receives messages from each thread.
# All json messages put onto the MESSAGES queue.Queue() will be forward to each applicable user thread
def broadcast_listener():
    while not STOP_COMMAND:
        message = MESSAGES.get()
        json_msg = json.loads(message)
        uuid = json_msg["uuid"]
        user = json_msg["user"]
        
        logging.info(uuid + {False: "(" + user + ")", True: ""}[user==uuid] + {False:": ",True:" "}[json_msg["action"]=="CONNECT"] + json_msg["message"])
        
        for i in ACTIVE_USERS:
            if i not in ACTIVE_USERNAMES:
                continue
            if uuid != i:
                if i in ACTIVE_USERS and isinstance(ACTIVE_USERS[i], queue.Queue):
                    try:
                        # send message to other users
                        ACTIVE_USERS[i].put(json_msg)
                    except BrokenPipeError as e:
                        # if the queue does not exist, then the user client has been forcibly closed without logging out already
                        LOGGING_OUT.put(i)
                        
        # remove users that have logged out
        while not LOGGING_OUT.empty():
            temp = LOGGING_OUT.get_nowait()
            if temp in ACTIVE_USERS:
                del ACTIVE_USERS[temp]
            if temp in ACTIVE_USERNAMES:
                del ACTIVE_USERNAMES[temp]
                

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", action="store", dest="SERVER_PORT", default=SERVER_PORT)
    args = parser.parse_args()
    SERVER_PORT = int(args.SERVER_PORT)

    # set up logging to file as well as stdout
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
    
    # start broadcast listener thread (monitoring MESSAGES queue)
    broadcast_listener_thread = threading.Thread(target=broadcast_listener)
    broadcast_listener_thread.start()
    THREADS.put_nowait(broadcast_listener_thread) 

    while not STOP_COMMAND:
        # accept new client, process CONNECT request and prepare new connection_thread from message
        logging.info("Ready to accept new client on main thread...")
        client_socket, addr = server_socket.accept()
        if not (message := client_socket.recv(1024).decode()).startswith("CONNECT"):
            client_socket.close()
            continue
        message = message[8:]
        try:
            json_msg = json.loads(message)
        except:
            logging.warning("Error parsing connection json request: " + str(message))
            continue
        uuid = json_msg["uuid"]
        user = json_msg["user"]
        ACTIVE_USERNAMES[uuid] = user
        # select new random port in range and send to client
        client_port = random.randrange(PORT_RANGE[0], PORT_RANGE[1])
        client_socket.sendall(str(client_port).encode())
        client_socket.close()
        new_thread = threading.Thread(target=connection_thread, args=(client_port,uuid,user,MESSAGES,ACTIVE_USERS[uuid]))
        new_thread.start()
        MESSAGES.put(message)
        THREADS.put_nowait(new_thread)

    while not THREADS.empty():
        THREADS.get().join()
    server_socket.close()
    logging.info("Server stopped.")
    sys.exit()
