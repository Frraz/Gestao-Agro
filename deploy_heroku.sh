#!/bin/bash

# Script para preparar o deploy do Sistema de Gestão de Fazendas no Heroku

echo "=== Preparando deploy para Heroku ==="

# Verificar se o Heroku CLI está instalado
if ! command -v heroku &> /dev/null; then
    echo "Heroku CLI não encontrado. Por favor, instale o Heroku CLI antes de continuar."
    echo "Instruções: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Verificar se está logado no Heroku
if ! heroku whoami &> /dev/null; then
    echo "Você não está logado no Heroku. Por favor, execute 'heroku login' antes de continuar."
    exit 1
fi

# Criar arquivo Procfile se não existir
if [ ! -f Procfile ]; then
    echo "Criando arquivo Procfile..."
    echo "web: gunicorn --chdir src main:app" > Procfile
    echo "✅ Arquivo Procfile criado"
fi

# Verificar se o gunicorn está nas dependências
if ! grep -q "gunicorn" requirements.txt; then
    echo "Adicionando gunicorn às dependências..."
    echo "gunicorn==20.1.0" >> requirements.txt
    echo "✅ Gunicorn adicionado às dependências"
fi

# Verificar se o pymysql está nas dependências
if ! grep -q "pymysql" requirements.txt; then
    echo "Adicionando pymysql às dependências..."
    echo "pymysql==1.0.2" >> requirements.txt
    echo "✅ PyMySQL adicionado às dependências"
fi

# Criar arquivo runtime.txt para especificar versão do Python
echo "python-3.11.0" > runtime.txt
echo "✅ Arquivo runtime.txt criado"

echo "=== Preparação para deploy concluída ==="
echo ""
echo "Para fazer o deploy no Heroku, execute os seguintes comandos:"
echo ""
echo "1. Criar um novo aplicativo Heroku (se ainda não existir):"
echo "   heroku create nome-do-seu-app"
echo ""
echo "2. Adicionar o banco de dados JawsDB MySQL:"
echo "   heroku addons:create jawsdb:kitefin"
echo ""
echo "3. Configurar as variáveis de ambiente:"
echo "   heroku config:set FLASK_APP=src/main.py"
echo "   heroku config:set FLASK_DEBUG=false"
echo "   heroku config:set DB_TYPE=mysql"
echo ""
echo "4. Obter a URL do JawsDB e configurar as variáveis de banco de dados:"
echo "   heroku config | grep JAWSDB_URL"
echo "   # A URL terá o formato: mysql://username:password@hostname:port/database"
echo "   # Configure as variáveis separadamente:"
echo "   heroku config:set DB_USERNAME=username"
echo "   heroku config:set DB_PASSWORD=password"
echo "   heroku config:set DB_HOST=hostname"
echo "   heroku config:set DB_PORT=port"
echo "   heroku config:set DB_NAME=database"
echo ""
echo "5. Configurar as variáveis de e-mail:"
echo "   heroku config:set MAIL_SERVER=smtp.gmail.com"
echo "   heroku config:set MAIL_PORT=587"
echo "   heroku config:set MAIL_USE_TLS=true"
echo "   heroku config:set MAIL_USERNAME=seu_email@gmail.com"
echo "   heroku config:set MAIL_PASSWORD=sua_senha_de_app"
echo "   heroku config:set MAIL_DEFAULT_SENDER=notificacoes@gestaofazendas.com.br"
echo ""
echo "6. Fazer o deploy:"
echo "   git init"
echo "   git add ."
echo "   git commit -m \"Deploy inicial\""
echo "   git push heroku main"
echo ""
echo "7. Abrir o aplicativo:"
echo "   heroku open"
echo ""
echo "Lembre-se de que você precisará de um repositório Git para fazer o deploy no Heroku."
