import socket
import threading
import time
import logging
import os

def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logger = logging.getLogger('PrintServer')
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler('logs/print_server.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

class PrintServer:
    def __init__(self):
        self.logger = setup_logging()
        self.current_user = None
        self.lock = threading.Lock()

    def handle_client(self, conn, addr):
        with conn:
            try:
                conn.settimeout(10)  # Timeout generoso
                data = conn.recv(1024).decode()
                
                if data.startswith("ENTER:"):
                    node_id = data.split(":")[1]
                    with self.lock:
                        if self.current_user == node_id:
                            conn.sendall(b"ALREADY_IN_CS")
                            return
                        
                        self.current_user = node_id
                        conn.sendall(b"ENTER_OK")
                        self.logger.info(f"ENTER - Node {node_id}")
                        
                        try:
                            exit_msg = conn.recv(1024).decode()
                            if exit_msg == "EXIT":
                                self.current_user = None
                                conn.sendall(b"EXIT_OK")
                                self.logger.info(f"EXIT - Node {node_id}")
                        except socket.timeout:
                            self.logger.error(f"Timeout waiting for EXIT from Node {node_id}")
                            self.current_user = None
                
            except Exception as e:
                self.logger.error(f"ERROR - {e}")
                with self.lock:
                    if self.current_user:
                        self.current_user = None

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', 5000))
            s.listen()
            self.logger.info("Print server started on port 5000")
            
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    server = PrintServer()
    server.start()