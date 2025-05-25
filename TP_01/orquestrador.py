import socket
import threading
import logging
import os


def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logger = logging.getLogger('Orquestrador')
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler('logs/orquestrador.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

class Orquestrador:
    def __init__(self):
        self.logger = setup_logging()
        self.current_user = None
        self.lock = threading.Lock()
        self.last_timestamp = 0
        self.last_printed_number = 0
        self.numbers_socket_lock = threading.Lock()

    def notify_numbers_service(self, message):
        with self.numbers_socket_lock:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect(("print_server", 5001))
                    s.sendall(message.encode())
                    if message.startswith("START"):
                        response = s.recv(1024).decode().strip()
                        if response.startswith("DONE"):
                            _, last_num = response.split(":")
                            self.last_printed_number = int(last_num)
            except Exception as e:
                self.logger.error(f"Failed to notify numbers service: {e}")

    def handle_client(self, conn, addr):
        with conn:
            try:
                conn.settimeout(10)
                data = conn.recv(1024).decode().strip()

                if data.startswith("ENTER:"):
                    parts = data.split(":")
                    node_id = parts[1].strip()
                    node_clock = int(parts[2]) if len(parts) > 2 else 0
                    with self.lock:
                        if self.current_user is not None:
                            self.logger.warning(f"CS conflict: Node {node_id} tried to enter but current user is {self.current_user}")
                            conn.sendall(b"SOMEONE_IS_IN_CS")
                            return

                        self.current_user = node_id
                        conn.sendall(b"ENTER_OK")
                        self.logger.info(f"ENTER - Node {node_id}")

                        self.notify_numbers_service(f"START:{node_id}:{self.last_printed_number}:{node_clock}")

                    try:
                        exit_msg = conn.recv(1024).decode().strip()
                        if exit_msg == "EXIT":
                            with self.lock:
                                self.current_user = None
                                self.logger.info(f"EXIT - Node {node_id}")
                                self.notify_numbers_service("STOP")
                                self.last_timestamp += 10
                            conn.sendall(b"EXIT_OK")
                    except socket.timeout:
                        self.logger.error(f"Timeout waiting for EXIT from Node {node_id}")
                        with self.lock:
                            self.current_user = None
                            self.notify_numbers_service("STOP")

            except Exception as e:
                self.logger.error(f"ERROR - {e}")
                with self.lock:
                    if self.current_user:
                        self.current_user = None
                        self.notify_numbers_service("STOP")

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', 5000))
            s.listen()
            self.logger.info("Orquestrador server started")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    server = Orquestrador()
    server.start()
