# Sistema de Exclusão Mútua Distribuído

Este projeto implementa um sistema de exclusão mútua entre múltiplos nós que acessam uma seção crítica (CS) compartilhada, simulada por um servidor de impressão. O controle de acesso é feito via comunicação por sockets usando o algoritmo de Ricart-Agrawala.

## Componentes
- **orquestrador.py**: Coordena a entrada e saída dos nós na seção crítica.
- **print_server.py**: Serviço de impressão que recebe do orquestrador o comando para imprimir uma sequência numérica.
- **distributed_node.py**: Representa um nó do sistema distribuído.
- **logs/**: Pasta de saída de logs de todos os componentes.

## Funcionalidades
- Exclusão mútua garantida entre os nós.
- Impressão de uma sequência de `k` números aleatórios (`1 ≤ k ≤ 10`) por nó, com intervalo de 0.5s entre cada número.
- Logs separados e detalhados para cada nó, o orquestrador e o serviço de impressão.
- Limpeza automática da pasta `logs/` a cada execução do orquestrador.

## Requisitos
- Docker e Docker Compose instalados.

## Executando o projeto

1. Clone o repositório:
```bash
git clone <repo>
cd <repo>
```

2. Suba os Conteiners:
```bash
docker-compose up --build
```

3. Para reiniciar completamente:
```bash
docker-compose down -v --remove-orphans
docker-compose up --build
```
ou 
```bash
docker-compose down && docker-compose up --build
```

4. Os logs estarão disponíveis em:

```bash
./logs/node_<ID>.log → logs de cada nó
./logs/orquestrador.log → logs do coordenador
./logs/print_service.log → logs do serviço de impressão
```

# Limpeza manual (opcional)
```bash
rm -rf logs/*
```
