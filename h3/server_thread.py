# Zach Weske
# CS 591, Spring 2023
# Homework 3
#   tls/redis server thread component

import socket
import ssl
import threading
import queue
import time
import json
import logging
import os
import redis
import traceback

PROGRAM_LOCATION = os.path.dirname(__file__)

# the thread spawned when a new client connects to the server
class connection_thread():
    def __init__(self, port, uuid, user, redis_host, redis_port, redis_pwd):
        self.user = user
        self.uuid = uuid
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, password=redis_pwd)
        self.socket_outgoing = queue.Queue()
        self.current_users = {}
        self.stop = False
        self.logged_out = False

        # start socket, add ssl layer to socket, and accept a client
        logging.info("Starting client listener thread on port " + str(port))
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("localhost", port))
        self.server_socket.listen(20)
        self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.ssl_context.load_cert_chain(certfile=os.path.join(PROGRAM_LOCATION, "rootCA.pem"), keyfile=os.path.join(PROGRAM_LOCATION, "rootCA.key"))
        self.sec_server_socket = self.ssl_context.wrap_socket(self.server_socket, server_side=True)#, ssl_version=ssl.PROTOCOL_TLSv1_2)  # TODO
        self.client_socket, addr = self.sec_server_socket.accept()  # blocking call to wait for a client to connect
        logging.info("User connect on port " + str(port) + ": " + self.uuid + {False: "(" + user + ")", True: "(without username)"}[user==uuid])

        # spawn new threads
        self.broadcast_listener = threading.Thread(target=self.listen_to_broadcast)
        self.client_listener = threading.Thread(target=self.accept_message)
        self.client_sender = threading.Thread(target=self.send_to_client)
        self.client_listener.start()
        self.broadcast_listener.start()
        self.client_sender.start()
        
        # tell other threads/clients that this user has connected properly
        time.sleep(0.3)
        login_msg = json.dumps({"user": self.user, "uuid": self.uuid, "action": "CONNECT", "data": " logged in!"})  # ref 1
        self.redis.publish("broadcast", login_msg)

        self.client_listener.join()  # wait for the client to close the connection before beginning the logout process
        self.logout()
        self.broadcast_listener.join()
        self.client_sender.join()
        logging.info("Logging out user " + self.uuid + {False: "(" + self.user + ")", True: ""}[self.user==self.uuid])
        self.client_socket.close()
        logging.info("Closed server connection " + str(port))# + "...")

    def logout(self):
        self.stop = True
        if self.logged_out:
            return
        try:
            message = json.dumps({"user": self.user, "uuid": self.uuid, "action": "QUIT", "data": " logged off"})  # ref 2
            self.redis.publish("broadcast", message)
            self.socket_outgoing.put(" ".encode())  # unblock self.send_to_client() and unblock potential blocked client-side thread
        except Exception:
            pass
        self.logged_out = True
    
    # used to monitor all outgoing messages and send them over the socket back to the client
    def send_to_client(self):
        while not self.stop:
            to_send = self.socket_outgoing.get()
            if len(to_send) == 0:
                continue
            try:
                self.client_socket.sendall(to_send)
            except BrokenPipeError as e:
                self.stop = True
            except Exception as e:
                logging.warning("server_thread.py:86  " + type(e).__name__ + ' ' + str(e))
                self.logout()
    
    # listens to the messages coming from other users or server messages on the redis broadcast channel
    #   relays information from rest of server to client
    def listen_to_broadcast(self):
        listener = self.redis.pubsub()
        listener.subscribe("broadcast")
        for message in listener.listen():
            if self.stop:
                break
            if not isinstance(message["data"], str):
                continue
            try:
                json_msg = json.loads(message["data"])  # pull message dict out of redis data dict
            except Exception as e:
                logging.warning("server_thread.py:102  redis msg decode warning: " + type(e).__name__ + ' ' + str(e))
                continue
            
            msg_user = json_msg["user"]
            msg_uuid = json_msg["uuid"]
            msg_data = json_msg["data"]
            msg_action = json_msg["action"]
            
            if msg_uuid == self.uuid:
                continue
            if msg_uuid == "SERVER" and msg_user == "server":
                if msg_action == "CONNECTED":
                    self.current_users = msg_data["users"]
                # implement future server-side messages here
                continue
            
            # implement future handling of various other actions here (if action == "FUTURE":)
            send_message_str = msg_user + {False:"",True:": "}[msg_action=="MESSAGE"] + msg_data
            self.socket_outgoing.put(send_message_str.encode())


    # accept messages sent from the client
    def accept_message(self):
        try:
            while not self.stop:
                try:
                    message = self.client_socket.recv(1024).decode()
                    try:
                        if message == "QUIT" or message == '\x04':
                            self.logout()
                        elif message == "LIST":
                            response = ("Logged in users: \n\t" + "\n\t".join(list(self.current_users.values()))).encode()
                            self.socket_outgoing.put(response)
                        elif message != "":
                            message = json.dumps({"user": self.user, "uuid": self.uuid, "action": "MESSAGE", "data": message})
                            self.redis.publish("broadcast", message)
                    except BrokenPipeError as e:  # catch garbage collected queue or closed socket (user logged out)
                        self.logout()             # TODO may not be necessary
                except Exception as e:
                    logging.error("server_thread.py:141  " + type(e).__name__ + ' ' + str(e))
                    traceback.print_exc()
                    self.logout()
            time.sleep(1)  # used to allow everything to settle before shutting down server thread
            self.logout()
        except Exception as e:
            logging.error("server_thread.py:147  " + type(e).__name__ + ' ' + str(e))

