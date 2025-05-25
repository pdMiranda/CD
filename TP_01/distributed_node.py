import argparse
import socket
import threading
import time
import random
import logging
import os
from queue import Queue

def setup_logging(node_id):
    if not os.path.exists('logs'):
        os.makedirs('logs')
    logger = logging.getLogger(f'Node{node_id}')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(f'logs/node_{node_id}.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger

class DistributedNode:
    CS_DURATION = 5

    def __init__(self, node_id, port, other_nodes):
        self.node_id = node_id
        self.port = port
        self.other_nodes = other_nodes
        self.logger = setup_logging(node_id)
        self.init_state()

    def init_state(self):
        self.clock = 0
        self.deferred = set()
        self.request_queue = []
        self.requesting = False
        self.in_cs = False
        self.awaiting_replies_from = set()
        self.reply_queue = Queue()
        self.lock = threading.Lock()
        self.running = True
        self.cs_start_time = 0

    def run_server(self):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.port))
            s.settimeout(1)
            s.listen()
            while self.running:
                try:
                    conn, addr = s.accept()
                    threading.Thread(target=self.handle_connection, args=(conn, addr)).start()
                except socket.timeout:
                    continue

    def handle_connection(self, conn, addr):
        with conn:
            try:
                data = conn.recv(1024).decode().strip()
                if data.startswith('REQUEST'):
                    self.handle_request(data)
                elif data.startswith('REPLY'):
                    self.handle_reply(data)
            except Exception as e:
                self.logger.error(f"Connection error: {e}")

    def handle_request(self, data):
        _, ts, node_id = data.split(',')
        ts, node_id = int(ts), int(node_id)
        with self.lock:
            self.update_clock(ts)
            self.request_queue.append((ts, node_id))
            self.request_queue.sort()
            if not self.requesting or self.should_grant(ts, node_id):
                self.send_reply(node_id)
                self.logger.info(f"Granted access to Node {node_id}")
            else:
                self.deferred.add(node_id)
                self.logger.info(f"Deferred Node {node_id}")

    def handle_reply(self, data):
        _, ts, node_id = data.split(',')
        ts, node_id = int(ts), int(node_id)
        with self.lock:
            self.update_clock(ts)
            if node_id in self.awaiting_replies_from:
                self.awaiting_replies_from.remove(node_id)
                self.logger.info(f"Received REPLY from Node {node_id} ({len(self.other_nodes) - len(self.awaiting_replies_from)}/{len(self.other_nodes)})")
            if not self.awaiting_replies_from:
                self.enter_cs()

    def request_loop(self):
        while self.running:
            time.sleep(random.uniform(1, 3))
            if random.random() > 0.5:
                self.request_cs()

    def request_cs(self):
        with self.lock:
            if self.requesting:
                return  # já solicitando
            self.clock += 1
            self.requesting = True
            self.awaiting_replies_from = {port - 5000 for _, port in self.other_nodes}
            self.request_queue.append((self.clock, self.node_id))
            self.request_queue.sort()
            self.logger.info(f"Requesting CS with timestamp {self.clock}")

            for host, port in self.other_nodes:
                threading.Thread(target=self.send_request, args=(host, port, self.clock), daemon=True).start()

    def send_request(self, host, port, ts):
        try:
            with socket.socket() as s:
                s.settimeout(2)
                s.connect((host, port))
                s.sendall(f"REQUEST,{ts},{self.node_id}".encode())
        except Exception as e:
            with self.lock:
                nid = port - 5000
                if nid in self.awaiting_replies_from:
                    self.awaiting_replies_from.remove(nid)
            self.logger.warning(f"Failed to connect to {host}:{port}")

    def enter_cs(self):
        if self.in_cs:
            return
        self.in_cs = True
        self.cs_start_time = time.time()
        self.logger.info("=== ENTERING CRITICAL SECTION ===")

        def watchdog():
            time.sleep(self.CS_DURATION + 2)
            if self.in_cs:
                self.logger.warning("CS watchdog triggered - forcing exit")
                self.exit_cs()

        threading.Thread(target=watchdog, daemon=True).start()
        threading.Thread(target=self._execute_cs, daemon=True).start()

    def _execute_cs(self):
        try:
            with socket.socket() as s:
                s.settimeout(3)
                s.connect(('orquestrador', 5000))
                s.sendall(f"ENTER:{self.node_id}:{self.clock}".encode())
                response = s.recv(1024).decode().strip()
                if response != "ENTER_OK":
                    self.logger.error(f"Server denied access: {response}")
                    return
                self.logger.info("=== IN CRITICAL SECTION ===")
                start = time.time()
                while time.time() - start < self.CS_DURATION:
                    time.sleep(0.1)
                s.sendall(b"EXIT")
                if s.recv(1024).decode().strip() == "EXIT_OK":
                    self.logger.info("=== EXITING CRITICAL SECTION ===")
        except Exception as e:
            self.logger.error(f"CS error: {e}")
        finally:
            self.exit_cs()

    def exit_cs(self):
        with self.lock:
            if not self.in_cs:
                return
            self.in_cs = False
            self.requesting = False
            self.awaiting_replies_from.clear()
            self.request_queue = [r for r in self.request_queue if r[1] != self.node_id]
            self.logger.info(f"Time spent in CS: {time.time() - self.cs_start_time}s")
            self.logger.info("=== LEFT CRITICAL SECTION ===")
            deferred = list(self.deferred)
            self.deferred.clear()
        for node_id in deferred:
            self.send_reply(node_id)

    def send_reply(self, node_id):
        host, port = next((h, p) for h, p in self.other_nodes if p == 5000 + node_id)
        try:
            with socket.socket() as s:
                s.settimeout(2)
                s.connect((host, port))
                s.sendall(f"REPLY,{self.clock},{self.node_id}".encode())
        except Exception:
            self.logger.warning(f"Failed to send reply to Node {node_id}")

    def update_clock(self, received_ts):
        self.clock = max(self.clock, received_ts) + 1

    def should_grant(self, ts, node_id):
        my_req = (self.clock, self.node_id)
        return (ts, node_id) < my_req

    def shutdown(self):
        self.running = False
        self.logger.info("Shutting down")

    def start(self):
        self.logger.info(f"Node {self.node_id} started on port {self.port}")
        threading.Thread(target=self.run_server, daemon=True).start()
        threading.Thread(target=self.request_loop, daemon=True).start()
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    other_nodes = [(f'node{i}', 5000 + i) for i in range(1, 7) if 5000 + i != args.port]
    node = DistributedNode(args.id, args.port, other_nodes)
    node.start()
