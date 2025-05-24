import argparse
import socket
import threading
import time
import random
import logging
from queue import Queue

class DistributedNode:
    def __init__(self, node_id, port, other_nodes):
        self.node_id = node_id
        self.port = port
        self.other_nodes = other_nodes
        self.setup_logging()
        self.init_state()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format=f'%(asctime)s - Node {self.node_id} - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger()

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
        self.logger.info(f"Starting node on port {self.port}")
        
        # Start server thread
        threading.Thread(target=self.run_server, daemon=True).start()
        
        # Start request loop
        threading.Thread(target=self.request_loop, daemon=True).start()
        
        # Start reply processor
        threading.Thread(target=self.process_replies, daemon=True).start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.port))
            s.listen()
            
            while self.running:
                try:
                    s.settimeout(1)
                    conn, addr = s.accept()
                    threading.Thread(target=self.handle_connection, args=(conn, addr)).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Server error: {e}")
                    break

    def handle_connection(self, conn, addr):
        with conn:
            try:
                data = conn.recv(1024).decode()
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
            self.logger.info(f"Received REQUEST from Node {node_id}")
            
            if not self.requesting or self.should_grant_request(int(ts), int(node_id)):
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
            time.sleep(random.uniform(2, 5))
            if random.random() > 0.5:
                self.request_cs()

    def request_cs(self):
        with self.lock:
            self.clock += 1
            self.requesting = True
            self.replies_received = 0
            self.request_queue.append((self.clock, self.node_id))
            self.request_queue.sort()
            self.logger.info(f"Requesting CS with timestamp {self.clock}")
            
            for host, port in self.other_nodes:
                try:
                    with socket.socket() as s:
                        s.settimeout(2)
                        s.connect((host, port))
                        s.sendall(f"REQUEST,{self.clock},{self.node_id}".encode())
                except Exception as e:
                    self.logger.warning(f"Failed to send to {host}:{port} - {e}")
                    self.replies_received += 1

    def process_replies(self):
        while self.running:
            node_id, ts = self.reply_queue.get()
            with self.lock:
                self.update_clock(ts)
                self.replies_received += 1
                
                if self.replies_received == len(self.other_nodes):
                    self.enter_cs()

    def enter_cs(self):
        self.in_cs = True
        self.logger.info("=== ENTERED CRITICAL SECTION ===")
        
        # Access shared resource
        try:
            with socket.socket() as s:
                s.connect(('print_server', 5000))
                s.sendall(f"{self.node_id}".encode())
        except Exception as e:
            self.logger.error(f"Failed to access print server: {e}")
        
        time.sleep(1)  # Simulate work
        self.exit_cs()

    def exit_cs(self):
        with self.lock:
            self.in_cs = False
            self.requesting = False
            self.request_queue.pop(0)
            
            for node_id in self.deferred:
                self.send_reply(node_id)
            self.deferred = []
        
        self.logger.info("=== LEFT CRITICAL SECTION ===")

    def shutdown(self):
        self.running = False
        self.logger.info("Shutting down node")

    def update_clock(self, received_ts):
        self.clock = max(self.clock, received_ts) + 1

    def should_grant_request(self, ts, node_id):
        return (self.request_queue[0][0] > ts or 
                (self.request_queue[0][0] == ts and self.request_queue[0][1] > node_id))

    def send_reply(self, node_id):
        host, port = next((h,p) for h,p in self.other_nodes if p == 5001 + node_id - 1)
        try:
            with socket.socket() as s:
                s.settimeout(2)
                s.connect((host, port))
                s.sendall(f"REPLY,{self.clock},{self.node_id}".encode())
        except Exception as e:
            self.logger.warning(f"Failed to send REPLY to Node {node_id}: {e}")

    def defer_reply(self, node_id):
        self.deferred.append(node_id)
        self.logger.info(f"Deferred reply to Node {node_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    
    # Other nodes' addresses (adjust ports if needed)
    other_nodes = [
        ('node1', 5001),
        ('node2', 5002),
        ('node3', 5003),
        ('node4', 5004),
        ('node5', 5005),
        ('node6', 5006)
    ]
    # Remove current node
    other_nodes = [n for n in other_nodes if n[1] != args.port]
    
    node = DistributedNode(args.id, args.port, other_nodes)
    node.start()