FROM python:3.9-slim

WORKDIR /app

# Primeiro copia apenas o requirements.txt para aproveitar o cache de construção
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || echo "No requirements to install"

# Agora copia o resto dos arquivos
COPY print_server.py distributed_node.py ./

CMD ["python", "distributed_node.py"]