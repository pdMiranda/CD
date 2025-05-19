import json
import subprocess
import sys
import time
import threading
from typing import List, Dict

def gerar_configuracao(num_nos: int) -> Dict:
    return {
        "servidor_impressao": {"host": "localhost", "port": 5000},
        "nos": [{"id": i, "host": "localhost", "port": 5000 + i} for i in range(1, num_nos + 1)]
    }

def iniciar_processo(comando, nome):
    """Inicia um processo com saída em tempo real"""
    return subprocess.Popen(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        text=True
    )

def exibir_saida(processo, prefixo):
    """Exibe a saída do processo em tempo real"""
    while True:
        linha = processo.stdout.readline()
        if linha:
            print(f"[{prefixo}] {linha.strip()}")
        erro = processo.stderr.readline()
        if erro:
            print(f"ERRO [{prefixo}] {erro.strip()}")
        if processo.poll() is not None:
            break

def main(num_nos: int):
    try:
        print(f"\n{'='*50}")
        print(f"Iniciando sistema com {num_nos} nós - SAÍDA EM TEMPO REAL")
        print(f"{'='*50}\n")

        # Gerar configuração
        config = gerar_configuracao(num_nos)
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)

        # Iniciar servidor
        servidor = iniciar_processo([sys.executable, "ServidorImpressao.py"], "Servidor")
        threading.Thread(target=exibir_saida, args=(servidor, "Servidor"), daemon=True).start()
        time.sleep(1)  # Espera o servidor iniciar

        # Iniciar nós
        processos = []
        for id_no in range(1, num_nos + 1):
            print(f"Iniciando nó {id_no}...")
            p = iniciar_processo([sys.executable, "NoDistribuido.py", str(id_no)], f"Nó {id_no}")
            processos.append(p)
            threading.Thread(target=exibir_saida, args=(p, f"Nó {id_no}"), daemon=True).start()
            time.sleep(0.3)  # Pequeno intervalo entre inicializações

        print(f"\n{'='*50}")
        print("Sistema rodando - Visualize as interações em tempo real abaixo")
        print(f"{'='*50}\n")

        # Manter o programa principal ativo
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nEncerrando todos os processos...")
        for p in processos:
            p.terminate()
        servidor.terminate()
        print("Sistema encerrado com sucesso.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            num_nos = int(sys.argv[1])
            if num_nos < 2:
                print("Erro: É necessário pelo menos 2 nós.")
                sys.exit(1)
            main(num_nos)
        except ValueError:
            print("Uso correto: python IniciadorNos.py <número_de_nós>")
    else:
        num_nos = int(input("Quantos nós deseja iniciar? (Mínimo 2): "))
        main(num_nos)