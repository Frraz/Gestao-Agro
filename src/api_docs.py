# src/api_docs.py

"""
Configuração da documentação automática via Flask-APISpec (Swagger/OpenAPI)
Para gerar e servir documentação interativa da API REST do sistema.

Uso:
- Importe e registre suas rotas após o app ser criado.
- Use decorators @doc e @marshal_with/@use_kwargs nas views para gerar schemas ricos.
- Exemplo de acesso: http://localhost:5000/swagger-ui/

Mais detalhes: https://flask-apispec.readthedocs.io/
"""

from flask_apispec import FlaskApiSpec

from src.main import create_app

app = create_app()
docs = FlaskApiSpec(app)

# Exemplo de registro de rota para documentação:
# from src.routes.documento import DocumentoResource
# docs.register(DocumentoResource, endpoint="documento_resource")

# DICA:
# - Para cada rota/resource, utilize o decorator @doc e schemas Marshmallow para descrição dos campos.

# Para servir a documentação Swagger UI, adicione no app principal:
# (No src/main.py, dentro de create_app)
# from flask_apispec.views import docs as apispec_docs
# app.register_blueprint(apispec_docs)
