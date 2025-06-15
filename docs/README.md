# Sistema de Gestão de Fazendas e Documentação

Este sistema foi desenvolvido para gerenciar fazendas, pessoas associadas e documentação relacionada, com foco em controle de vencimentos e organização de documentos.

## Funcionalidades

- **Cadastro de pessoas** com associação a múltiplas fazendas/áreas
- **Cadastro de fazendas/áreas** com informações de matrícula, tamanho e tipo de posse
- **Gestão de documentação** com controle de datas de emissão e vencimento
- **Upload e armazenamento seguro** de arquivos de documentos
- **Sistema de notificação** de vencimentos via interface
- **Interface administrativa** completa com dashboard e filtros

## Requisitos Técnicos

- Python 3.8+
- MySQL ou outro banco de dados relacional
- Dependências Python listadas em `requirements.txt`

## Estrutura do Projeto

```
sistema-gestao-fazendas/
├── src/
│   ├── models/       # Modelos de banco de dados
│   ├── routes/       # Rotas e APIs
│   ├── templates/    # Templates HTML
│   ├── static/       # Arquivos estáticos (CSS, JS)
│   ├── utils/        # Utilitários
│   └── main.py       # Ponto de entrada da aplicação
├── uploads/          # Diretório para upload de arquivos
└── requirements.txt  # Dependências do projeto
```

## Instruções de Implantação

Abaixo estão as instruções para implantar o sistema em diferentes plataformas:

### Configuração Local

1. Clone o repositório
2. Crie um ambiente virtual: `python -m venv venv`
3. Ative o ambiente virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instale as dependências: `pip install -r requirements.txt`
5. Configure as variáveis de ambiente para o banco de dados:
   ```
   export DB_USERNAME=seu_usuario
   export DB_PASSWORD=sua_senha
   export DB_HOST=localhost
   export DB_PORT=3306
   export DB_NAME=nome_do_banco
   ```
6. Execute a aplicação: `python src/main.py`

### Implantação no Heroku

1. Crie uma conta no [Heroku](https://heroku.com/)
2. Instale o [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
3. Faça login no Heroku: `heroku login`
4. Crie um novo aplicativo: `heroku create nome-do-app`
5. Adicione um banco de dados MySQL:
   ```
   heroku addons:create cleardb:ignite --app nome-do-app
   ```
6. Obtenha a URL do banco de dados:
   ```
   heroku config --app nome-do-app | grep CLEARDB_DATABASE_URL
   ```
7. Configure as variáveis de ambiente:
   ```
   heroku config:set DB_USERNAME=usuario_do_cleardb
   heroku config:set DB_PASSWORD=senha_do_cleardb
   heroku config:set DB_HOST=host_do_cleardb
   heroku config:set DB_PORT=3306
   heroku config:set DB_NAME=nome_do_banco_cleardb
   ```
8. Crie um arquivo `Procfile` na raiz do projeto com o conteúdo:
   ```
   web: gunicorn --chdir src main:app
   ```
9. Adicione `gunicorn` ao `requirements.txt`
10. Faça o deploy:
    ```
    git add .
    git commit -m "Deploy to Heroku"
    git push heroku main
    ```

### Implantação no PythonAnywhere

1. Crie uma conta no [PythonAnywhere](https://www.pythonanywhere.com/)
2. Faça upload do código via ZIP ou Git
3. Crie um novo aplicativo web:
   - Selecione Flask
   - Escolha a versão do Python
   - Configure o caminho para o arquivo WSGI
4. Configure o ambiente virtual:
   ```
   mkvirtualenv --python=python3.8 venv
   pip install -r requirements.txt
   ```
5. Configure o banco de dados MySQL:
   - Crie um novo banco de dados no painel do PythonAnywhere
   - Configure as variáveis de ambiente no arquivo WSGI
6. Configure o diretório de uploads para ser gravável
7. Reinicie o aplicativo web

### Implantação no Render

1. Crie uma conta no [Render](https://render.com/)
2. Crie um novo serviço web
3. Conecte ao repositório Git ou faça upload do código
4. Configure o serviço:
   - Tipo: Web Service
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --chdir src main:app`
5. Adicione as variáveis de ambiente para o banco de dados
6. Implante o serviço

## Configuração do Banco de Dados

O sistema está configurado para usar MySQL, mas pode ser adaptado para outros bancos de dados suportados pelo SQLAlchemy.

Para inicializar o banco de dados, o sistema cria automaticamente as tabelas necessárias na primeira execução.

## Manutenção

- **Backups**: Faça backups regulares do banco de dados e dos arquivos de upload
- **Atualizações**: Mantenha as dependências atualizadas para evitar problemas de segurança
- **Monitoramento**: Verifique regularmente os logs para identificar possíveis problemas

## Suporte

Para suporte ou dúvidas sobre o sistema, entre em contato com o desenvolvedor.

## Licença

Este projeto é fornecido como está, sem garantias expressas ou implícitas.
