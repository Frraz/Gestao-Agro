# src/api_docs.py

"""
Documentação da API usando Swagger/OpenAPI
"""

from flask import Blueprint, jsonify, current_app, render_template

# Tratamento de importações com verificação para dependências opcionais
try:
    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin
    from apispec_webframeworks.flask import FlaskPlugin
    from flask_swagger_ui import get_swaggerui_blueprint
    SWAGGER_AVAILABLE = True
except ImportError:
    # Informar sobre as dependências ausentes
    import logging
    logging.warning("""
        Dependências para documentação da API não estão instaladas.
        Instale-as com:
        pip install apispec apispec-webframeworks flask-swagger-ui marshmallow
    """)
    SWAGGER_AVAILABLE = False

# Configuração global
api_version = '1.0.0'
api_title = 'API de Gestão Agrícola'
api_description = """
API RESTful para o Sistema de Gestão Agrícola.
Fornece endpoints para gerenciar fazendas, documentos, endividamentos e notificações.
"""

# Definição do blueprint principal
api_docs_bp = Blueprint('api_docs', __name__, url_prefix='/api')

# Criamos um flag para rastrear se o blueprint já foi registrado
_blueprint_registered = False

def init_docs(app):
    """
    Inicializa a documentação da API com Swagger
    
    Args:
        app: Aplicação Flask
    """
    global _blueprint_registered
    
    # Verifica se o blueprint já foi registrado para evitar registrá-lo novamente
    if _blueprint_registered:
        app.logger.warning("Documentação da API já foi inicializada anteriormente")
        return
    
    # Verifica se as dependências estão disponíveis
    if not SWAGGER_AVAILABLE:
        app.logger.warning("Documentação da API desativada. Dependências ausentes.")
        
        # Registra apenas o blueprint básico para o status da API
        @api_docs_bp.route('/status')
        def api_status():
            return jsonify({
                'status': 'online',
                'version': api_version,
                'app_name': current_app.name,
                'docs_available': False,
                'reason': 'Dependências ausentes'
            })
            
        app.register_blueprint(api_docs_bp)
        _blueprint_registered = True
        return None
    
    # A partir daqui, só executa se SWAGGER_AVAILABLE for True
    # Cria a especificação da API
    spec = APISpec(
        title=api_title,
        version=api_version,
        info={"description": api_description},
        openapi_version="3.0.2",
        plugins=[FlaskPlugin(), MarshmallowPlugin()],
    )

    # Rota para o JSON da especificação OpenAPI
    @api_docs_bp.route('/openapi.json')
    def get_apispec():
        return jsonify(spec.to_dict())

    # Rota para status da API
    @api_docs_bp.route('/status')
    def api_status():
        return jsonify({
            'status': 'online',
            'version': api_version,
            'app_name': current_app.name,
            'docs_available': True
        })
    
    # Configura o blueprint do Swagger UI
    swagger_ui = get_swaggerui_blueprint(
        '/api/docs',               # URL para acessar o UI
        '/api/openapi.json',       # URL do JSON da especificação
        config={
            'app_name': api_title,
            'docExpansion': "list",
            'deepLinking': True
        }
    )
    
    # Registra os blueprints
    app.register_blueprint(api_docs_bp)
    app.register_blueprint(swagger_ui, url_prefix='/api/docs')
    
    # Marca o blueprint como registrado para evitar registro duplicado
    _blueprint_registered = True
    
    app.logger.info("Documentação da API disponível em /api/docs")
    
    # Documenta as rotas existentes - usando documentação manual em vez de extração automática
    _document_routes_manually(spec)
    
    return spec


def _document_routes_manually(spec):
    """
    Documenta as rotas manualmente sem tentar extrair das funções de view
    
    Args:
        spec: Especificação da API
    """
    # Se as dependências não estiverem disponíveis, não faz nada
    if not SWAGGER_AVAILABLE:
        return
        
    # Rotas para documentos
    documento_tag = {
        'name': 'Documentos',
        'description': 'Operações relacionadas a documentos'
    }
    spec.tag(documento_tag)
    
    # Adiciona manualmente as rotas sem tentar usar o path_helper do Flask
    # Documentos
    spec.components.schema(
        "Documento",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "nome": {"type": "string"},
                "tipo": {"type": "string"},
                "data_emissao": {"type": "string", "format": "date"},
                "data_vencimento": {"type": "string", "format": "date"},
                "caminho_arquivo": {"type": "string"},
                "pessoa_id": {"type": "integer"},
                "fazenda_id": {"type": "integer"},
                "ativo": {"type": "boolean"}
            }
        }
    )
    
    spec.components.schema(
        "DocumentoCreate",
        {
            "type": "object",
            "required": ["nome", "tipo", "data_vencimento"],
            "properties": {
                "nome": {"type": "string"},
                "tipo": {"type": "string"},
                "data_emissao": {"type": "string", "format": "date"},
                "data_vencimento": {"type": "string", "format": "date"},
                "pessoa_id": {"type": "integer"},
                "fazenda_id": {"type": "integer"},
                "observacoes": {"type": "string"}
            }
        }
    )

    # Adiciona o caminho /api/documentos manualmente
    documentos_path = {
        "get": {
            "tags": ["Documentos"],
            "summary": "Lista todos os documentos",
            "description": "Retorna uma lista paginada de documentos",
            "parameters": [
                {
                    "name": "page",
                    "in": "query",
                    "description": "Número da página",
                    "schema": {"type": "integer", "default": 1}
                },
                {
                    "name": "per_page",
                    "in": "query",
                    "description": "Itens por página",
                    "schema": {"type": "integer", "default": 10}
                }
            ],
            "responses": {
                "200": {
                    "description": "Lista de documentos",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Documento"}
                                    },
                                    "total": {"type": "integer"},
                                    "page": {"type": "integer"},
                                    "per_page": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "post": {
            "tags": ["Documentos"],
            "summary": "Criar novo documento",
            "description": "Cria um novo documento no sistema",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/DocumentoCreate"}
                    }
                }
            },
            "responses": {
                "201": {
                    "description": "Documento criado com sucesso",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Documento"}
                        }
                    }
                },
                "400": {
                    "description": "Dados inválidos"
                }
            }
        }
    }
    spec._paths["/api/documentos"] = documentos_path
    
    # Rotas para endividamentos
    endividamento_tag = {
        'name': 'Endividamentos',
        'description': 'Operações relacionadas a endividamentos'
    }
    spec.tag(endividamento_tag)
    
    spec.components.schema(
        "Endividamento",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "banco": {"type": "string"},
                "numero_proposta": {"type": "string"},
                "data_contratacao": {"type": "string", "format": "date"},
                "data_vencimento_final": {"type": "string", "format": "date"},
                "valor_operacao": {"type": "number", "format": "float"},
                "taxa_juros": {"type": "number", "format": "float"},
                "tipo_taxa_juros": {"type": "string", "enum": ["mes", "ano"]}
            }
        }
    )
    
    # Adiciona o caminho /api/endividamentos manualmente
    endividamentos_path = {
        "get": {
            "tags": ["Endividamentos"],
            "summary": "Lista todos os endividamentos",
            "description": "Retorna uma lista paginada de endividamentos",
            "parameters": [
                {
                    "name": "page",
                    "in": "query",
                    "description": "Número da página",
                    "schema": {"type": "integer", "default": 1}
                },
                {
                    "name": "per_page",
                    "in": "query",
                    "description": "Itens por página",
                    "schema": {"type": "integer", "default": 10}
                }
            ],
            "responses": {
                "200": {
                    "description": "Lista de endividamentos",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Endividamento"}
                                    },
                                    "total": {"type": "integer"},
                                    "page": {"type": "integer"},
                                    "per_page": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    spec._paths["/api/endividamentos"] = endividamentos_path
    
    # Rotas para notificações
    notificacao_tag = {
        'name': 'Notificações',
        'description': 'Operações relacionadas a notificações'
    }
    spec.tag(notificacao_tag)
    
    spec.components.schema(
        "NotificacaoEndividamento",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "endividamento_id": {"type": "integer"},
                "tipo_notificacao": {"type": "string"},
                "data_envio": {"type": "string", "format": "date-time"},
                "enviado": {"type": "boolean"},
                "emails": {"type": "array", "items": {"type": "string"}}
            }
        }
    )
    
    spec.components.schema(
        "NotificacaoDocumento",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "documento_id": {"type": "integer"},
                "tipo_notificacao": {"type": "string"},
                "data_envio": {"type": "string", "format": "date-time"},
                "enviado": {"type": "boolean"},
                "emails": {"type": "array", "items": {"type": "string"}}
            }
        }
    )
    
    # Adiciona o caminho /api/notificacoes/pendentes manualmente
    notificacoes_path = {
        "get": {
            "tags": ["Notificações"],
            "summary": "Lista notificações pendentes",
            "description": "Retorna uma lista de notificações pendentes",
            "responses": {
                "200": {
                    "description": "Lista de notificações",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "endividamentos": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/NotificacaoEndividamento"}
                                    },
                                    "documentos": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/NotificacaoDocumento"}
                                    },
                                    "total": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    spec._paths["/api/notificacoes/pendentes"] = notificacoes_path