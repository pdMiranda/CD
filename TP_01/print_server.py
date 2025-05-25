import socket
import threading
import time
import logging
import os
import random

def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs', exist_ok=True) 

    logger = logging.getLogger('PrintService') 
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler('logs/print_service.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

class NumberPrinter:
    def __init__(self):
        self.logger = setup_logging()
        self.active = False
        self.current_node = None
        self.current_node_time = 0
        self.sequence = []
        self.thread = None
        self.lock = threading.Lock()

    def start_sequence(self, node_id, start_value, node_timestamp):
        with self.lock:
            if self.active:
                self.logger.warning("Number printer already active.")
                return f"STARTED:{start_value}"

            self.active = True
            self.current_node = node_id
            self.current_node_time = node_timestamp

            k = random.randint(1, 10)
            self.sequence = list(range(start_value + 1, start_value + 1 + k))

            self.thread = threading.Thread(target=self.print_server)
            self.thread.start()

            return f"STARTED:{self.sequence[-1]}"

    def print_server(self):
        self.logger.info(f"Node {self.current_node} started printing numbers. | time: {self.current_node_time} | k = {len(self.sequence)}")

        for num in self.sequence:
            with self.lock:
                if not self.active:
                    break
                self.logger.info(f"Node {self.current_node} >> {num} | {num - self.current_node_time}")
            time.sleep(0.5)

        with self.lock:
            last = self.sequence[-1] if self.sequence else self.current_node_time
            self.active = False
            self.logger.info(f"Finished printing for Node {self.current_node}\n")
            try:
                self.response_conn.sendall(f"DONE:{last}".encode())
                self.response_conn.close()
            except Exception as e:
                self.logger.error(f"Failed to send DONE message: {e}")
            finally:
                self.sequence = []
                self.current_node = None


    def stop(self):
        with self.lock:
            self.logger.info(f"Stopped printing for Node {self.current_node}\n")
            self.active = False
            self.current_node = None

    def handle_client(self, conn):
        try:
            data = conn.recv(1024).decode().strip()

            if data.startswith("START:"):
                parts = data.split(":")
                if len(parts) == 4:
                    _, node_id, _, node_timestamp = parts
                    start_value = int(node_timestamp)
                else:
                    _, node_id, _ = parts
                    start_value = int(time.time())

                self.response_conn = conn
                response = self.start_sequence(node_id, start_value, start_value)
                return

            elif data == "STOP":
                self.stop()
                conn.sendall(b"STOPPED")
                conn.close()

        except Exception as e:
            self.logger.error(f"Error: {e}")


    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', 5001))
            s.listen()
            self.logger.info("Print Server service started\n")

            while True:
                conn, _ = s.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    server = NumberPrinter()
    server.start()
