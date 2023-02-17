# Zach Weske
# CS 591, Spring 2023
# Homework 2
#   tls client component

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
import ssl
import time
import argparse
import uuid
import json
import threading
import sys
import signal
try:
    import curses
except ModuleNotFoundError as e:
    print("Running on Windows? Install 'windows-curses' with")
    print("  pip install windows-curses")
    exit()



SERVER_ADDR = "localhost"
SERVER_PORT = 8888

class chat_client():
    def __init__(self, SERVER_ADDR, SERVER_PORT, CUSTOM_PORT, UUID, USER):
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
            # print('Press Ctrl+C')
            # signal.pause()
            stdscr = curses.initscr()
            # curses.cbreak()
            self.print_window = curses.newwin(curses.LINES - 1, curses.COLS, 0, 0)
            self.print_window.scrollok(True)
            self.input_window = curses.newwin(1, curses.COLS, curses.LINES - 1, 0)
            self.print_window.refresh()
            self.to_print_after = []
            
            self.STOP_COMMAND = False
            self.UUID = UUID
            self.USER = USER
            
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # client_socket = ssl.wrap_socket(client_socket, ssl_version=ssl.PROTOCOL_TLSv1_2)
            client_socket.connect((SERVER_ADDR, SERVER_PORT))
            # client_socket.send(b"CONNECT " + UUID.encode())
            message = ("CONNECT " + json.dumps({"user": self.USER, "uuid": self.UUID, "action": "CONNECT", "data": "has joined"})).encode()
            client_socket.send(message)
            new_port = int(client_socket.recv(1024).decode())
            client_socket.close()
            self.print("Attempting to begin new connection on port " + str(new_port))

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # self.client_socket = ssl.wrap_socket(self.client_socket, ssl_version=ssl.PROTOCOL_SSLv23)
            time.sleep(0.2)
            if(CUSTOM_PORT != 0):
                new_port = CUSTOM_PORT
            self.client_socket.connect((SERVER_ADDR, new_port))
            self.print("Connected to server!")
            
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
            # curses.nocbreak()
            curses.endwin()
            for item in self.to_print_after:
                print(item)
        except ConnectionRefusedError as e:
            try:
                # curses.nocbreak()
                curses.endwin()
            except:
                pass
            print("Client error: connection refused- is the server running?")
        except Exception as e:
            try:
                # curses.nocbreak()
                curses.endwin()
            except:
                pass
            print("Client error: " + type(e).__name__)
            # traceback.print_exc()
        
    def signal_handler(self, sig, frame):
        # print('You pressed Ctrl+C!')
        self.print("Quitting, press a key followed by ctrl+z to continue...")
        self.STOP_COMMAND = True
        try:
            self.client_socket.close()
        except:
            pass
        sys.exit(0)

    def print(self, to_print):
        try:
            self.print_window.addstr(str(to_print) + '\n')
            self.print_window.refresh()
        except:
            pass

    def print_e(self, to_print):
        self.to_print_after.append(to_print)
        self.print(to_print)
        
    def monitor_socket(self):
        while not self.STOP_COMMAND:
            try:
                data = self.client_socket.recv(1024).decode()
                if data == '':
                    self.STOP_COMMAND = True
                    self.print("Connection closed by server, press any key to quit...")
                    continue
                self.print({True: "No data received", False: data}[data == ''])  # '\r' + '\033[K' + 
                # if not self.STOP_COMMAND:
                #     print("> ")
            # except socket.timeout:
            #     continue
            except Exception as e:
                self.print_e(type(e).__name__ + ' ' + str(e))
                self.STOP_COMMAND = True
                continue
            
    def monitor_input(self):
        # while not self.STOP_COMMAND:
        #     try:
        #         chat = input("> ")
        #     except EOFError as e:
        #         chat = '\x04'
        #     if chat.strip() == "":
        #         continue
        #     self.client_socket.send((chat).encode())  # TODO convert to action instead of message with json?
        #     if chat == '\x04' or chat == "QUIT":
        #         print("Exiting client...")
        #         self.STOP_COMMAND = True
        #         continue
        # while (not self.STOP_COMMAND and char != 4 and stuff != "QUIT" and stuff != "^D" and stuff != '\x04'):
        while not self.STOP_COMMAND:
            self.input_window.addstr("> ")
            chat = ""
            char = self.input_window.getch()
            while char != 10 and char != 4 and not self.STOP_COMMAND:
                if char < 127 and char > 31:
                    chat += chr(char)
                elif char == 127:
                    self.input_window.move(0, max(2, self.input_window.getyx()[1] - 3))
                    self.input_window.addstr("   ")
                    self.input_window.move(0, max(2, self.input_window.getyx()[1] - 3))
                    self.input_window.refresh()
                    chat = chat[:-1]
                char = self.input_window.getch()

            if char == 4 or chat == "QUIT" or chat == '\x04' or chat == "^D":
                self.STOP_COMMAND = True
                chat = "QUIT"
            if chat != "":
                try:
                    self.client_socket.send((chat).encode())
                except:
                    pass
            self.print(chat)
            self.input_window.clear()
            # self.print_window.addstr(str(chat) + '\n')
            # self.print_window.refresh()
        self.print("Exiting client, press any key to close...")
        self.input_window.getch()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    UUID = str(uuid.uuid4())

    parser.add_argument("-a", "--address", action="store", dest="SERVER_ADDR", default=SERVER_ADDR)
    parser.add_argument("-p", "--port",    action="store", dest="SERVER_PORT", default=SERVER_PORT)
    parser.add_argument("-u", "--user", "--username", "--name", action="store", dest="USER", default=UUID)
    parser.add_argument("-c", "--custom_port", action="store", dest="CUSTOM_PORT", default=0)
    args = parser.parse_args()

    client_connection_obj = chat_client(args.SERVER_ADDR, int(args.SERVER_PORT), int(args.CUSTOM_PORT), UUID, args.USER)
