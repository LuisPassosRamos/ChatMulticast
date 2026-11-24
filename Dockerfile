FROM python:3.12-slim

# Defina a saída não-bufferizada do Python
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto para o contêiner
COPY client.py server.py ./

# Usa a variável NODE_TYPE para decidir qual script executar
CMD ["sh", "-c", "python -u ${NODE_TYPE}.py"]
