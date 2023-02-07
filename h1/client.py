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
import json
import threading
import traceback

SERVER_ADDR = "localhost"
SERVER_PORT = 8888

class chat_client():
    def __init__(self, SERVER_ADDR, SERVER_PORT, CUSTOM_PORT, UUID, USER):
        try:
            self.STOP_COMMAND = False
            self.UUID = UUID
            self.USER = USER
            
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_ADDR, SERVER_PORT))
            # client_socket.send(b"CONNECT " + UUID.encode())
            message = ("CONNECT " + json.dumps({"user": self.USER, "uuid": self.UUID, "action": "CONNECT", "message": "has joined"})).encode()
            client_socket.send(message)
            new_port = int(client_socket.recv(1024).decode())
            client_socket.close()
            print("Attempting to begin new connection on port", new_port)

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            time.sleep(0.2)
            if(CUSTOM_PORT != 0):
                print(CUSTOM_PORT)
                new_port = CUSTOM_PORT
            self.client_socket.connect((SERVER_ADDR, new_port))
            
            printing_thread = threading.Thread(target=self.monitor_socket)
            printing_thread.start()
            input_thread = threading.Thread(target=self.monitor_input)
            input_thread.start()
            
            input_thread.join()
            self.STOP_COMMAND = True
            
            self.client_socket.close()
            # self.client_socket.shutdown(socket.SHUT_WR)
            # self.client_socket.setblocking(0)
            printing_thread.join()

        except Exception as e:
            print("Client error: " + type(e).__name__)
            # traceback.print_exc()
        
        
    def monitor_socket(self):
        while not self.STOP_COMMAND:
            try:
                data = self.client_socket.recv(1024).decode()
                if data == '':
                    self.STOP_COMMAND = True
                    print("Connection closed by server, press enter to quit...")
                    continue
                print({True: "No data received", False: data}[data == ''])  # '\r' + '\033[K' + 
                if not self.STOP_COMMAND:
                    print("> ")
            # except socket.timeout:
            #     continue
            except Exception as e:
                print(type(e).__name__ + ' ' + str(e))
                self.STOP_COMMAND = True
                continue
            
    def monitor_input(self):
        while not self.STOP_COMMAND:
            try:
                chat = input("> ")
            except EOFError as e:
                chat = '\x04'
            if chat.strip() == "":
                continue
            self.client_socket.send((chat).encode())
            if chat == '\x04' or chat == "QUIT":
                print("Exiting client...")
                self.STOP_COMMAND = True
                continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    UUID = str(uuid.uuid4())

    parser.add_argument("-a", "--address", action="store", dest="SERVER_ADDR", default=SERVER_ADDR)
    parser.add_argument("-p", "--port",    action="store", dest="SERVER_PORT", default=SERVER_PORT)
    parser.add_argument("-u", "--user", "--username", "--name", action="store", dest="USER", default=UUID)
    parser.add_argument("-c", "--custom_port", action="store", dest="CUSTOM_PORT", default=0)
    args = parser.parse_args()

    client_connection_obj = chat_client(args.SERVER_ADDR, int(args.SERVER_PORT), int(args.CUSTOM_PORT), UUID, args.USER)
