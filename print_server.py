import socket
import threading
import logging

class PrintServer:
    def __init__(self, port=5000):
        self.port = port
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - PrintServer - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger()

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.port))
            s.listen()
            self.logger.info(f"Print server started on port {self.port}")
            
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        with conn:
            try:
                data = conn.recv(1024).decode()
                if data:
                    self.logger.info(f"Node {data} accessed the shared resource")
            except Exception as e:
                self.logger.error(f"Error handling client: {e}")

if __name__ == "__main__":
    PrintServer().start()