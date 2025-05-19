import socket
import threading
import time
import random
import json
import sys
from typing import List, Dict
from datetime import datetime
import functools

# Decorator para forçar flush da saída
def flush_output(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        ret = f(*args, **kwargs)
        sys.stdout.flush()
        sys.stderr.flush()
        return ret
    return wrapped

class NoDistribuido:
    @flush_output
    def log(self, mensagem: str):
        current_time = time.strftime("%H:%M:%S")
        print(f"{self.cor}[{current_time}] Nó {self.id}: {mensagem}{self.CORES['reset']}")
        
    def __init__(self, id_no: int, port: int, outros_nos: List[Dict], servidor_impressao: Dict):
        self.id = id_no
        self.port = port
        self.outros_nos = outros_nos
        self.servidor_impressao = servidor_impressao
        
        self.clock_lamport = 0
        self.requisitando = False
        self.permissoes_recebidas = 0
        self.requisicoes_pendentes = []
        self.lock = threading.Lock()
        
        # Cores para melhor visualização
        self.CORES = {
            'vermelho': '\033[91m',
            'verde': '\033[92m',
            'amarelo': '\033[93m',
            'azul': '\033[94m',
            'magenta': '\033[95m',
            'ciano': '\033[96m',
            'branco': '\033[97m',
            'reset': '\033[0m'
        }
        
        self.cor = list(self.CORES.values())[self.id % len(self.CORES)]
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
    def log(self, mensagem: str):
        current_time = time.strftime("%H:%M:%S")
        msg = f"{self.cor}[{current_time}] Nó {self.id}: {mensagem}{self.CORES['reset']}"
        print(msg, flush=True)  # Força o flush imediato
    
    def incrementar_clock(self):
        with self.lock:
            self.clock_lamport += 1
            return self.clock_lamport
    
    def obter_clock(self):
        with self.lock:
            return self.clock_lamport
    
    def atualizar_clock(self, timestamp_recebido):
        with self.lock:
            self.clock_lamport = max(self.clock_lamport, timestamp_recebido) + 1
    
    def iniciar(self):
        # Thread para escutar mensagens de outros nós
        threading.Thread(target=self.escutar_mensagens, daemon=True).start()
        
        # Thread para simular acesso ao recurso
        threading.Thread(target=self.simular_acesso_recurso, daemon=True).start()
        
        # Manter o programa rodando
        while True:
            time.sleep(1)
    
    def escutar_mensagens(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', self.port))
            s.listen()
            
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.processar_mensagem, args=(conn,)).start()
    
    def processar_mensagem(self, conn):
        with conn:
            data = conn.recv(1024).decode()
            
            if data.startswith("REQUEST"):
                _, timestamp, id_remetente = data.split(',')
                self.log(f"Recebido REQUEST do nó {id_remetente} (timestamp: {timestamp})")
                self.tratar_requisicao(int(timestamp), int(id_remetente))
            elif data.startswith("OK"):
                _, id_remetente = data.split(',')
                self.log(f"Recebido OK do nó {id_remetente}")
                self.tratar_resposta(int(id_remetente))
    
    def tratar_requisicao(self, timestamp: int, id_remetente: int):
        self.atualizar_clock(timestamp)
        
        with self.lock:
            prioridade_remetente = (timestamp, id_remetente)
            minha_prioridade = (self.obter_clock(), self.id)
            
            self.log(f"Processando REQUEST do nó {id_remetente}...")
            
            if self.requisitando and prioridade_remetente < minha_prioridade:
                self.log(f"Adiando resposta para nó {id_remetente} (minha prioridade é maior)")
                self.requisicoes_pendentes.append((timestamp, id_remetente))
            else:
                self.log(f"Enviando OK para nó {id_remetente}")
                self.enviar_resposta(id_remetente)
    
    def tratar_resposta(self, id_remetente: int):
        with self.lock:
            self.permissoes_recebidas += 1
            self.log(f"Permissões recebidas: {self.permissoes_recebidas}/{len(self.outros_nos)}")
            
            if self.requisitando and self.permissoes_recebidas == len(self.outros_nos):
                self.log("Todas as permissões recebidas! Acessando recurso compartilhado...")
                self.acessar_recurso_compartilhado()
    
    def enviar_requisicao(self):
        timestamp = self.incrementar_clock()
        mensagem = f"REQUEST,{timestamp},{self.id}"
        
        with self.lock:
            self.requisitando = True
            self.permissoes_recebidas = 0
            self.requisicoes_pendentes = []
        
        self.log(f"Enviando REQUEST para todos os nós (timestamp: {timestamp})")
        
        for no in self.outros_nos:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((no['host'], no['port']))
                    s.sendall(mensagem.encode())
            except Exception as e:
                self.log(f"Erro ao enviar requisição para nó {no['id']}: {e}")
    
    def enviar_resposta(self, id_destino: int):
        for no in self.outros_nos:
            if no['id'] == id_destino:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((no['host'], no['port']))
                        s.sendall(f"OK,{self.id}".encode())
                    self.log(f"OK enviado para nó {id_destino}")
                except Exception as e:
                    self.log(f"Erro ao enviar OK para nó {id_destino}: {e}")
                break
    
    def acessar_recurso_compartilhado(self):
        # Gerar k aleatório entre 1 e 10
        k = random.randint(1, 10)
        self.log(f"Acessando recurso compartilhado para imprimir {k} números")
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.servidor_impressao['host'], self.servidor_impressao['port']))
                mensagem = f"{self.id},{self.obter_clock()},{k}"
                s.sendall(mensagem.encode())
        except Exception as e:
            self.log(f"Erro ao acessar servidor de impressão: {e}")
        
        with self.lock:
            self.requisitando = False
            self.permissoes_recebidas = 0
            
            # Processar requisições pendentes
            pendentes = len(self.requisicoes_pendentes)
            if pendentes > 0:
                self.log(f"Processando {pendentes} requisições pendentes")
            
            for timestamp, id_remetente in self.requisicoes_pendentes:
                self.enviar_resposta(id_remetente)
            
            self.requisicoes_pendentes = []
    
    def simular_acesso_recurso(self):
        while True:
            time.sleep(2)
            
            if random.random() > 0.5:  # 50% de chance de solicitar acesso
                self.log("Decidiu solicitar acesso ao recurso")
                self.enviar_requisicao()

if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
    
    # Obter ID do nó do argumento de linha de comando
    if len(sys.argv) > 1:
        id_no = int(sys.argv[1])
    else:
        id_no = int(input("Digite o ID deste nó: "))
    
    no_config = next(no for no in config['nos'] if no['id'] == id_no)
    outros_nos = [no for no in config['nos'] if no['id'] != id_no]
    
    no = NoDistribuido(
        id_no=no_config['id'],
        port=no_config['port'],
        outros_nos=outros_nos,
        servidor_impressao=config['servidor_impressao']
    )
    
    no.iniciar()