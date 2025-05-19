import socket
import threading
import time
from datetime import datetime

class ServidorImpressao:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.ultimo_timestamp = 0
        self.lock = threading.Lock()
        self.sessao_critica_em_uso = False
        self.processo_atual = None
        
    def iniciar(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"\n{'='*50}")
            print(f"Servidor de impressão iniciado em {self.host}:{self.port}")
            print(f"{'='*50}\n")
            
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.tratar_cliente, args=(conn, addr)).start()
    
    def tratar_cliente(self, conn, addr):
        with conn:
            data = conn.recv(1024).decode()
            id_processo, timestamp, k = map(int, data.split(','))
            
            with self.lock:
                # Mostrar status da seção crítica
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"\n{'#'*50}")
                print(f"[{current_time}] Processo {id_processo} INICIOU acesso à seção crítica")
                self.sessao_critica_em_uso = True
                self.processo_atual = id_processo
                
                print(f"\nProcesso {id_processo} iniciando impressão:")
                
                # Garante que a sequência comece após o último timestamp
                inicio = max(timestamp, self.ultimo_timestamp)
                
                for i in range(k):
                    numero = inicio + i + 1
                    print(f"[{time.time()}] Processo {id_processo}: {numero}")
                    time.sleep(0.5)
                
                self.ultimo_timestamp = inicio + k
                
                # Mostrar término da seção crítica
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{current_time}] Processo {id_processo} CONCLUIU acesso à seção crítica")
                self.sessao_critica_em_uso = False
                self.processo_atual = None
                print(f"{'#'*50}\n")

if __name__ == "__main__":
    servidor = ServidorImpressao('localhost', 5000)
    servidor.iniciar()