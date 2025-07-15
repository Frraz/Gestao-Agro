# Dockerfile otimizado para Sistema de Gestão Agro com Flask, Gunicorn e MySQL
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema (necessárias para MySQL e compilar pacotes Python)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários (logs, uploads)
RUN mkdir -p logs uploads/documentos

# Expor porta padrão para o Railway (usa variável de ambiente PORT)
EXPOSE 5000

# Definir variáveis de ambiente padrão
ENV FLASK_APP=src/main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Comando de entrada: executa migrations e inicia Gunicorn
CMD flask db upgrade && gunicorn src.main:app --bind 0.0.0.0:${PORT:-5000}