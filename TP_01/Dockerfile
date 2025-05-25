FROM python:3.9-slim

WORKDIR /app

# Copia o requirements.txt primeiro
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || echo "No requirements to install"

# Copia TODOS os arquivos do projeto
COPY . .

# Definido apenas para testes locais — sobrescrito no docker-compose
CMD ["python", "distributed_node.py"]