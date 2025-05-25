# Sistema de Exclusão Mútua Distribuído

Este projeto implementa um sistema de exclusão mútua entre múltiplos nós que acessam uma seção crítica (CS) compartilhada, simulada por um servidor de impressão. O controle de acesso é feito via comunicação por sockets usando o algoritmo de Ricart-Agrawala.

## Componentes
- **orquestrador.py**: Simula a seção crítica.
- **print_server.py**: Imprime os numeros 
- **distributed_node.py**: Representa um nó do sistema distribuído.
- **logs/**: Pasta de saída de logs.

## Funcionalidades
- Exclusão mútua garantida.
- Controle de prioridade por timestamp e ID do nó.
- Logs detalhados para cada nó e para o servidor central.
- Limpeza automática da pasta `logs/` a cada execução.

## Requisitos
- Docker e Docker Compose instalados.

## Executando o projeto

1. Clone o repositório:
```bash
git clone <repo>
cd <repo>
```

2. Suba os containers:
```bash
docker-compose up --build
```

3. Reset de Sistema 
```bash
docker-compose down && docker-compose up --build
```

4. Os logs de cada nó estarão disponíveis em `./logs/node_<ID>.log`,o do servidor em `./logs/orquestrador.log` e os numeros em `./logs/print_server.log`.

## Observações
- O sistema é totalmente autônomo e simula requisições aleatórias à seção crítica.
- O watchdog evita deadlocks forçando a saída de um nó após tempo limite.

## Limpeza manual (opcional)
Para limpar logs manualmente:
```bash
rm -rf logs/*
