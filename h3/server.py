# Zach Weske
# CS 591, Spring 2023
# Homework 3
#   tls/redis server component

""" Usage: 
    python server.py
    - runs simple server on localhost:SERVER_PORT

    python server.py --help
    - gives additional usage information
"""

SERVER_PORT = 8888
PORT_RANGE = [9001, 9999]
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PWD = 'swdfjygkubhlnjm'


import socket
import ssl
import sys
import threading
import queue
import argparse
import random
import json
import signal
import logging
import os
import redis
import server_thread


""" developer notes

1. chat sent from client to server thread over TCP/TLS as encoded string
2. message sent from server thread to broadcast channel as json.dumps (incl uuid, user, action, chat data)
3. message received by all other server threads via broadcast channel and 
        sent to their client using TCP if applicable

redis message["data"] format (JSON):
    uuid: str
    user: str
    data: str
    action: str

    potential message actions:
        MESSAGE, QUIT, CONNECT:
            sent from client/thread owning msg["uuid"]
            hard coded messages for CONNECT/QUIT found in server_thread.py at  # ref 1 and  # ref 2
        CONNECTED:
            sent from server broadcast_listener() to threads via redis broadcast channel
            hard coded messages found in this file at  # ref 3
            they listen for this by checking msg["user"] and msg["uuid"] - see  # ref 4
"""

PROGRAM_LOCATION = os.path.dirname(__file__)

class chat_server():
    def __init__(self):
        # signal.signal(signal.SIGINT, self.signal_handler)
        self.STOP_COMMAND = False
        try:
            self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT,
                                decode_responses=True, password=REDIS_PWD)
        except redis.exceptions.ConnectionError:
            print("Connection to redis database refused.")
            print("  Is it running and are connection settings correct? use '--help' for more information")
            sys.exit()
        except ConnectionRefusedError:
            print("Connection to redis database refused.")
            print("  Is it running and are connection settings correct? use '--help' for more information")
            sys.exit()
        except ConnectionError:
            print("Connection to redis database refused.")
            print("  Is it running and are connection settings correct? use '--help' for more information")
            sys.exit()
        # input()
        self.active_usernames = {}  # pairs uuid to username

        # set up logging to file as well as stdout
        logging.basicConfig(filename=os.path.join(PROGRAM_LOCATION, 'server.log'), 
                            encoding='utf-8', level=logging.DEBUG, filemode='w',
                            format='%(asctime)s - %(levelname)-7s - %(message)s')
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        
        # start broadcast listener thread (monitoring redis broadcast channel)
        self.broadcast_listener_thread = threading.Thread(target=self.broadcast_listener)
        self.broadcast_listener_thread.start()

        self.accept_new_clients()
        
        self.broadcast_listener_thread.join()
        self.sec_server_socket.close()
        logging.info("Server stopped.")
        
    
    def accept_new_clients(self):
        self.threads = queue.Queue()
        # Prepare initial sever socket
        logging.info("Starting server on port " +  str(SERVER_PORT))
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("localhost", SERVER_PORT))
        server_socket.listen(20)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=os.path.join(PROGRAM_LOCATION, "rootCA.pem"), 
                                    keyfile=os.path.join(PROGRAM_LOCATION, "rootCA.key"))
        self.sec_server_socket = ssl_context.wrap_socket(server_socket, server_side=True)#, ssl_version=ssl.PROTOCOL_TLSv1_2)  # TODO
        logging.info("Serving on localhost:" + str(SERVER_PORT))

        while not self.STOP_COMMAND:
            # accept new client, process CONNECT request and prepare new connection_thread from message
            logging.info("Ready to accept new client on main thread...")
            client_socket, addr = self.sec_server_socket.accept()
            if not (message := client_socket.recv(1024).decode()).startswith("CONNECT"):
                client_socket.close()
                continue
            message = message[8:]
            try:
                json_msg = json.loads(message)
            except:
                logging.warning("server.py:125  error parsing connection json request: " + str(message))
                continue
            # select new random port in range and send to client
            client_port = random.randrange(PORT_RANGE[0], PORT_RANGE[1])
            client_socket.sendall(str(client_port).encode())
            client_socket.close()
            new_thread = threading.Thread(target=server_thread.connection_thread, args=(
                client_port,json_msg["uuid"],json_msg["user"],REDIS_HOST,REDIS_PORT,REDIS_PWD))
            new_thread.start()
            self.threads.put_nowait(new_thread)

        while not self.threads.empty():
            self.threads.get().join()
    
    # receives messages from each thread via redis "broadcast" channel
    def broadcast_listener(self):
        listener = self.redis.pubsub()
        listener.subscribe("broadcast")
        for message in listener.listen():
            if self.STOP_COMMAND:
                return
            if not isinstance(message["data"], str):
                continue
            try:
                json_msg = json.loads(message["data"])  # pull this dict out of redis data dict
            except Exception as e:
                logging.warning("server.py:151  redis msg decode warning: " + type(e).__name__ + ' ' + str(e))
                continue
            
            uuid = json_msg["uuid"]
            user = json_msg["user"]
            action = json_msg["action"]

            if uuid == "SERVER" and user == "server":  # ref 4
                continue
            if action == "CONNECT":
                self.active_usernames[uuid] = user
                msg = json.dumps({"user": "server", "uuid": "SERVER", "action": "CONNECTED", "data": {"users": self.active_usernames}})  # ref 3
                self.redis.publish("broadcast", msg)
            elif action == "QUIT":
                if uuid in self.active_usernames:
                    del self.active_usernames[uuid]
                msg = json.dumps({"user": "server", "uuid": "SERVER", "action": "CONNECTED", "data": {"users": self.active_usernames}})  # ref 3
                self.redis.publish("broadcast", msg)

            logging.info(uuid + {False: "(" + user + ")", True: ""}[user==uuid] + 
                        {False:"",True:": "}[action=="MESSAGE"] + json_msg["data"])

    # # attempt to gracefully handle ctrl+c
    # def signal_handler(self, sig, frame):
    #     self.STOP_COMMAND = True
    #     self.redis.publish("broadcast", 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", action="store", dest="PORT", default=SERVER_PORT, 
                        help="The port to run the server on. Default: " + str(SERVER_PORT))
    parser.add_argument("-r", "--redis_host", action="store", dest="REDIS_HOST", default=REDIS_HOST, 
                        help="The redis host. Default: " + str(REDIS_HOST))
    parser.add_argument("-rp", "--redis_port", action="store", dest="REDIS_PORT", default=REDIS_PORT,
                        help="The port redis is running on. Default: " + str(REDIS_PORT))
    parser.add_argument("-rpwd", "--redis_pwd", action="store", dest="REDIS_PWD", default=REDIS_PWD,
                        help="The password to be used with redis. Default: " + str(REDIS_PWD))
    args = parser.parse_args()
    REDIS_PORT = int(args.REDIS_PORT)
    SERVER_PORT = int(args.PORT)
    REDIS_HOST = args.REDIS_HOST
    REDIS_PWD = args.REDIS_PWD
    
    t = chat_server()
    
    
