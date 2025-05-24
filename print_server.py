import socket
import threading
import logging
import os
import glob

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
    
    def setup_logging(node_id=None):
        # Criar pasta de logs se não existir
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Configurar logging
        logger = logging.getLogger('print_server' if node_id is None else f'node_{node_id}')
        logger.setLevel(logging.INFO)
        
        # Formato do log
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Handler para arquivo (um por nó)
        file_handler = logging.FileHandler(f'logs/{"print_server" if node_id is None else f"node_{node_id}"}.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger

if __name__ == "__main__":
    PrintServer().start()