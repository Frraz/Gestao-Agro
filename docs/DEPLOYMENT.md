# Guia de Deploy - Sistema de Gestão de Fazendas

Este guia fornece instruções detalhadas para implantar o Sistema de Gestão de Fazendas em diferentes ambientes.

## Deploy Local

### Requisitos
- Python 3.8+
- MySQL 5.7+ ou SQLite
- Servidor SMTP para envio de e-mails (opcional)

### Passos para Deploy Local

1. **Configurar o ambiente virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Instalar dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variáveis de ambiente**:
   - Copie o arquivo `.env.example` para `.env`
   - Edite o arquivo `.env` com suas configurações

4. **Inicializar o banco de dados**:
   - Para SQLite (desenvolvimento):
     ```bash
     export DB_TYPE=sqlite
     python src/main.py
     ```
   - Para MySQL:
     ```bash
     ./setup_mysql.sh
     ```

5. **Executar a aplicação**:
   ```bash
   python src/main.py
   ```

## Deploy no Heroku

### Requisitos
- Conta no Heroku
- Heroku CLI instalado
- Git instalado

### Passos para Deploy no Heroku

1. **Preparar o ambiente**:
   ```bash
   ./deploy_heroku.sh
   ```

2. **Criar um novo aplicativo Heroku**:
   ```bash
   heroku create nome-do-seu-app
   ```

3. **Adicionar o banco de dados JawsDB MySQL**:
   ```bash
   heroku addons:create jawsdb:kitefin
   ```

4. **Configurar variáveis de ambiente**:
   ```bash
   heroku config:set FLASK_APP=src/main.py
   heroku config:set FLASK_DEBUG=false
   heroku config:set DB_TYPE=mysql
   ```

5. **Configurar variáveis do banco de dados**:
   - Obter a URL do JawsDB:
     ```bash
     heroku config | grep JAWSDB_URL
     ```
   - A URL terá o formato: `mysql://username:password@hostname:port/database`
   - Configurar as variáveis separadamente:
     ```bash
     heroku config:set DB_USERNAME=username
     heroku config:set DB_PASSWORD=password
     heroku config:set DB_HOST=hostname
     heroku config:set DB_PORT=port
     heroku config:set DB_NAME=database
     ```

6. **Configurar variáveis de e-mail**:
   ```bash
   heroku config:set MAIL_SERVER=smtp.gmail.com
   heroku config:set MAIL_PORT=587
   heroku config:set MAIL_USE_TLS=true
   heroku config:set MAIL_USERNAME=seu_email@gmail.com
   heroku config:set MAIL_PASSWORD=sua_senha_de_app
   heroku config:set MAIL_DEFAULT_SENDER=notificacoes@gestaofazendas.com.br
   ```

7. **Fazer o deploy**:
   ```bash
   git init
   git add .
   git commit -m "Deploy inicial"
   git push heroku main
   ```

8. **Abrir o aplicativo**:
   ```bash
   heroku open
   ```

## Deploy em Outras Plataformas

### Railway

1. Crie uma conta no [Railway](https://railway.app/)
2. Conecte seu repositório GitHub
3. Configure as variáveis de ambiente
4. Deploy automático a partir do repositório

### Render

1. Crie uma conta no [Render](https://render.com/)
2. Crie um novo Web Service
3. Conecte seu repositório GitHub
4. Configure as variáveis de ambiente
5. Deploy automático a partir do repositório

### PythonAnywhere

1. Crie uma conta no [PythonAnywhere](https://www.pythonanywhere.com/)
2. Crie um novo Web App com Flask
3. Configure o WSGI file para apontar para `src/main.py`
4. Configure as variáveis de ambiente
5. Reinicie o Web App

## Solução de Problemas

### Problemas de Conexão com o Banco de Dados

- **Erro**: "Can't connect to MySQL server"
  - **Solução**: Verifique se o servidor MySQL está em execução e se as credenciais estão corretas

- **Erro**: "Access denied for user"
  - **Solução**: Verifique as permissões do usuário no MySQL

### Problemas de Envio de E-mail

- **Erro**: "SMTP authentication failed"
  - **Solução**: Verifique as credenciais de e-mail e se o servidor SMTP permite aplicativos menos seguros

- **Erro**: "Connection refused"
  - **Solução**: Verifique se o servidor SMTP está acessível e se a porta está correta

### Problemas no Heroku

- **Erro**: "Application Error" ao acessar o aplicativo
  - **Solução**: Verifique os logs com `heroku logs --tail`

- **Erro**: "No web processes running"
  - **Solução**: Verifique se o Procfile está correto e se o dyno está em execução

## Manutenção

### Backup do Banco de Dados

- **MySQL Local**:
  ```bash
  mysqldump -u username -p gestao_fazendas > backup.sql
  ```

- **Heroku**:
  ```bash
  heroku pg:backups:capture
  heroku pg:backups:download
  ```

### Atualização da Aplicação

1. Faça as alterações necessárias no código
2. Teste localmente
3. Faça o commit das alterações
4. Para o Heroku:
   ```bash
   git push heroku main
   ```
