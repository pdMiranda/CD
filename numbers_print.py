import socket
import threading
import time
import logging
import os
import random

class NumberPrinter:
    def __init__(self):
        self.logger = self.setup_logging()
        self.active = False
        self.current_node = None
        self.sequence = []
        self.thread = None
        self.lock = threading.Lock()

    def setup_logging(self):
        if not os.path.exists('logs'):
            os.makedirs('logs')
        logger = logging.getLogger('NumberPrinter')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh = logging.FileHandler('logs/numbers.log')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.addHandler(logging.StreamHandler())
        return logger

    def start_sequence(self, node_id, start_value):
        with self.lock:
            if self.active:
                self.logger.warning("Number printer already active.")
                return f"STARTED:{start_value}"
            self.active = True
            self.current_node = node_id
            k = random.randint(1, 10)
            self.sequence = list(range(start_value + 1, start_value + 1 + k))
            self.thread = threading.Thread(target=self.print_numbers)
            self.thread.start()
            return f"STARTED:{self.sequence[-1]}"

    def print_numbers(self):
        for num in self.sequence:
            with self.lock:
                if not self.active:
                    break
                timestamp = int(time.time())
                self.logger.info(f"Node {self.current_node} | {timestamp} >> {num}")
            time.sleep(0.5)

        with self.lock:
            self.active = False
            self.sequence = []

    def stop(self):
        with self.lock:
            self.logger.info(f"Stopped printing for Node {self.current_node}")
            self.active = False
            self.current_node = None

    def handle_client(self, conn):
        with conn:
            try:
                data = conn.recv(1024).decode().strip()
                if data.startswith("START:"):
                    _, node_id, start_val = data.split(":")
                    response = self.start_sequence(node_id, int(start_val))
                    conn.sendall(response.encode())
                elif data == "STOP":
                    self.stop()
                    conn.sendall(b"STOPPED")
            except Exception as e:
                self.logger.error(f"Error: {e}")

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', 5001))
            s.listen()
            self.logger.info("Number printer service started on port 5001")
            while True:
                conn, _ = s.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    NumberPrinter().start()
