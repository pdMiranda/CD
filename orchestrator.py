import subprocess
import sys
import time
import socket
from threading import Thread

def find_free_port(start_port, max_attempts=100):
    """Encontra uma porta livre começando de start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    raise Exception(f"Não encontrou porta livre após {max_attempts} tentativas")

def start_node(node_id, base_port):
    port = find_free_port(base_port + node_id - 1)
    cmd = f"python distributed_node.py --id {node_id} --port {port} --base-port {base_port}"
    print(f"Iniciando Node {node_id} na porta {port}")
    subprocess.Popen(cmd, shell=True)

def main():
    if len(sys.argv) < 2:
        print("Uso: python orchestrator.py <num_nodes> [base_port]")
        return

    num_nodes = int(sys.argv[1])
    base_port = int(sys.argv[2]) if len(sys.argv) > 2 else 5001

    # Inicia o servidor de impressão
    print("Iniciando Print Server na porta 5000")
    subprocess.Popen("python print_server.py", shell=True)
    time.sleep(1)  # Espera o servidor iniciar

    # Inicia os nós
    threads = []
    for node_id in range(1, num_nodes + 1):
        t = Thread(target=start_node, args=(node_id, base_port))
        t.start()
        threads.append(t)
        time.sleep(0.2)  # Pequeno delay entre inicializações

    for t in threads:
        t.join()

    print(f"Sistema distribuído com {num_nodes} nós iniciado")

if __name__ == "__main__":
    main()