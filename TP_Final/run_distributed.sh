#!/bin/bash

# Define o endereço do nó mestre (onde o rank 0 será executado)
# Para testes locais, é localhost. Em um cluster, seria o IP do nó mestre.
export MASTER_ADDR="localhost"
export MASTER_PORT="29500" # Porta para comunicação

# Número total de processos que participarão do treinamento.
# Neste exemplo, 3 processos: 1 para o rank 0, 1 para o rank 1, 1 para o rank 2.
# Geralmente, este é o número de GPUs ou CPUs que você quer usar.
export WORLD_SIZE=3 

# Ativa o ambiente virtual
source venv/Scripts/activate

echo "Iniciando treinamento distribuído com PyTorch DDP..."

# Comando para iniciar o treinamento distribuído
# -m torch.distributed.launch é o utilitário do PyTorch
# --nproc_per_node: número de processos a serem lançados neste nó.
#                   Como estamos em uma única máquina, será WORLD_SIZE.
#                   Em um cluster, cada máquina rodaria com nproc_per_node
#                   igual ao número de CPUs/GPUs dessa máquina.
python -m torch.distributed.launch \
    --nproc_per_node=$WORLD_SIZE \
    --master_addr=$MASTER_ADDR \
    --master_port=$MASTER_PORT \
    main.py

echo "Treinamento distribuído concluído."

deactivate