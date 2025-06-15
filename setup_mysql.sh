#!/bin/bash

# Script para configuração e teste do Sistema de Gestão de Fazendas com MySQL

echo "=== Configurando ambiente para testes locais com MySQL ==="

# Verificar se o MySQL está instalado
if ! command -v mysql &> /dev/null; then
    echo "MySQL não encontrado. Por favor, instale o MySQL antes de continuar."
    exit 1
fi

# Criar banco de dados se não existir
echo "Criando banco de dados 'gestao_fazendas' se não existir..."
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS gestao_fazendas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Verificar se o arquivo .env existe, caso contrário criar a partir do exemplo
if [ ! -f .env ]; then
    echo "Criando arquivo .env a partir do exemplo..."
    cp .env.example .env
    echo "Por favor, edite o arquivo .env com suas credenciais de banco de dados e e-mail."
fi

# Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt

# Verificar se o pymysql está instalado
if ! pip show pymysql &> /dev/null; then
    echo "Instalando pymysql..."
    pip install pymysql
fi

# Configurar variáveis de ambiente para MySQL
export DB_TYPE=mysql
export FLASK_APP=src/main.py
export FLASK_DEBUG=true

echo "=== Configuração concluída ==="
echo "Para iniciar a aplicação, execute:"
echo "python src/main.py"
echo ""
echo "Certifique-se de que o MySQL está em execução e as credenciais no arquivo .env estão corretas."
