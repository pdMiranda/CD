import argparse
import socket
import threading
import time
import random
import logging
import os
from queue import Queue

def setup_logging(node_id=None):
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logger = logging.getLogger('print_server' if node_id is None else f'node_{node_id}')
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler(f'logs/{"print_server" if node_id is None else f"node_{node_id}"}.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

class DistributedNode:
    def __init__(self, node_id, port, other_nodes):
        self.node_id = node_id
        self.port = port
        self.other_nodes = other_nodes
        self.logger = setup_logging(node_id)
        self.init_state()

    def init_state(self):
        self.clock = 0
        self.deferred = []
        self.request_queue = []
        self.replies_received = 0
        self.requesting = False
        self.in_cs = False
        self.reply_queue = Queue()
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        self.logger.info(f"Node {self.node_id} started on port {self.port}")
        
        # Server thread
        threading.Thread(target=self.run_server, daemon=True).start()
        
        # Request loop
        threading.Thread(target=self.request_loop, daemon=True).start()
        
        # Reply processor
        threading.Thread(target=self.process_replies, daemon=True).start()
        
        # Keep alive
        try:
            while self.running:
                time.sleep(0.1)  # Loop mais rápido
        except KeyboardInterrupt:
            self.shutdown()

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.port))
            s.settimeout(1)  # Timeout para não bloquear
            s.listen()
            
            while self.running:
                try:
                    conn, addr = s.accept()
                    threading.Thread(target=self.handle_connection, args=(conn, addr)).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Server error: {e}")
                    break

    def handle_connection(self, conn, addr):
        try:
            with conn:
                data = conn.recv(1024).decode()
                if not data:
                    return
                
                if data.startswith('REQUEST'):
                    self.handle_request(data)
                elif data.startswith('REPLY'):
                    self.handle_reply(data)
        except Exception as e:
            self.logger.error(f"Connection error: {e}")

    def handle_request(self, data):
        _, ts, node_id = data.split(',')
        with self.lock:
            self.update_clock(int(ts))
            
            # Responde imediatamente se possível
            if not self.requesting or self.should_grant(int(ts), int(node_id)):
                self.send_reply(int(node_id))
            else:
                self.defer_reply(int(node_id))

    def handle_reply(self, data):
        _, ts, node_id = data.split(',')
        with self.lock:
            self.update_clock(int(ts))
            self.reply_queue.put((int(node_id), int(ts)))

    def request_loop(self):
        while self.running:
            time.sleep(random.uniform(1, 2))  # Intervalo mais curto
            if random.random() > 0.5:
                self.request_cs()

    def request_cs(self):
        with self.lock:
            self.clock += 1
            self.requesting = True
            self.replies_received = 0
            self.request_queue.append((self.clock, self.node_id))
            self.request_queue.sort()
            self.logger.info(f"Requesting CS (TS: {self.clock})")
            
            # Envia requests em threads separadas para não bloquear
            for host, port in self.other_nodes:
                threading.Thread(
                    target=self.send_request,
                    args=(host, port, self.clock),
                    daemon=True
                ).start()

    def send_request(self, host, port, ts):
        try:
            with socket.socket() as s:
                s.settimeout(1)
                s.connect((host, port))
                s.sendall(f"REQUEST,{ts},{self.node_id}".encode())
        except Exception as e:
            with self.lock:
                self.replies_received += 1
            self.logger.warning(f"Failed to send to {host}:{port}")

    def process_replies(self):
        while self.running:
            node_id, ts = self.reply_queue.get()
            with self.lock:
                self.update_clock(ts)
                self.replies_received += 1
                self.logger.info(f"Got REPLY from Node {node_id} ({self.replies_received}/{len(self.other_nodes)})")
                
                if self.replies_received == len(self.other_nodes):
                    threading.Thread(target=self.enter_cs, daemon=True).start()

    def enter_cs(self):
        self.in_cs = True
        self.logger.info("=== ENTERED CRITICAL SECTION ===")
        
        try:
            with socket.socket() as s:
                s.settimeout(0.5)
                s.connect(('print_server', 5000))
                s.sendall(f"{self.node_id}".encode())
        except Exception as e:
            self.logger.error(f"Print server error: {e}")
        finally:
            self.exit_cs()

    def exit_cs(self):
        with self.lock:
            self.in_cs = False
            self.requesting = False
            if self.request_queue:
                self.request_queue.pop(0)
            
            # Envia replies diferidos em threads separadas
            for node_id in self.deferred:
                threading.Thread(
                    target=self.send_reply,
                    args=(node_id,),
                    daemon=True
                ).start()
            self.deferred = []
        
        self.logger.info("=== LEFT CRITICAL SECTION ===")

    def send_reply(self, node_id):
        host, port = next((h,p) for h,p in self.other_nodes if p == 5001 + node_id - 1)
        try:
            with socket.socket() as s:
                s.settimeout(1)
                s.connect((host, port))
                s.sendall(f"REPLY,{self.clock},{self.node_id}".encode())
        except Exception as e:
            self.logger.warning(f"Failed to send REPLY to Node {node_id}")

    def update_clock(self, received_ts):
        self.clock = max(self.clock, received_ts) + 1

    def should_grant(self, ts, node_id):
        return (self.request_queue[0][0] > ts or 
                (self.request_queue[0][0] == ts and self.request_queue[0][1] > node_id))

    def defer_reply(self, node_id):
        self.deferred.append(node_id)
        self.logger.info(f"Deferred reply to Node {node_id}")

    def shutdown(self):
        self.running = False
        self.logger.info("Shutting down")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    
    other_nodes = [('node{}'.format(i), 5000 + i) for i in range(1, 7)]
    other_nodes = [n for n in other_nodes if n[1] != args.port]
    
    node = DistributedNode(args.id, args.port, other_nodes)
    node.start()