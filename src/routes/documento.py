# /src/routes/documentos.py

import datetime
import traceback

from flask import Blueprint, current_app, jsonify, request, render_template
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.models.db import db
from src.models.documento import Documento, TipoDocumento
from src.models.fazenda import Fazenda
from src.models.pessoa import Pessoa
from src.utils.email_service import enviar_email_teste
from src.utils.notificacao_utils import calcular_proximas_notificacoes_programadas

# Blueprints
documento_bp = Blueprint("documento", __name__, url_prefix="/api/documentos")
admin_documentos_bp = Blueprint("admin_documentos", __name__, url_prefix="/admin/documentos")

def data_valida(data_str):
    """Valida e converte string de data para objeto date."""
    try:
        return datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
    except ValueError:
        return None

# -------- API ROUTES --------

@documento_bp.route("/", methods=["GET"])
def listar_documentos():
    """Lista todos os documentos cadastrados."""
    try:
        documentos = Documento.query.all()
        resultado = []
        for documento in documentos:
            fazenda_nome = documento.fazenda.nome if documento.fazenda else None
            fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
            pessoa_nome = documento.pessoa.nome if documento.pessoa else None

            resultado.append(
                {
                    "id": documento.id,
                    "nome": documento.nome,
                    "tipo": documento.tipo.value,
                    "tipo_personalizado": documento.tipo_personalizado,
                    "data_emissao": documento.data_emissao.isoformat(),
                    "data_vencimento": (
                        documento.data_vencimento.isoformat()
                        if documento.data_vencimento
                        else None
                    ),
                    "fazenda_id": documento.fazenda_id,
                    "fazenda_nome": fazenda_nome,
                    "fazenda_matricula": fazenda_matricula,
                    "pessoa_id": documento.pessoa_id,
                    "pessoa_nome": pessoa_nome,
                    "emails_notificacao": documento.emails_notificacao,
                    "prazos_notificacao": documento.prazos_notificacao,
                    "esta_vencido": documento.esta_vencido,
                    "proximo_vencimento": documento.proximo_vencimento,
                }
            )
        return jsonify(resultado)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar documentos: {str(e)}")
        return jsonify({"erro": "Erro ao listar documentos", "detalhes": str(e)}), 500

@documento_bp.route("/<int:id>", methods=["GET"])
def obter_documento(id):
    """Obtém detalhes de um documento específico."""
    try:
        documento = Documento.query.get_or_404(id)

        fazenda_nome = documento.fazenda.nome if documento.fazenda else None
        fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
        pessoa_nome = documento.pessoa.nome if documento.pessoa else None

        prazos = documento.prazos_notificacao if documento.prazos_notificacao else [30, 15, 7, 1]
        prazos = [int(p) for p in prazos]
        enviados = []  # Popule com histórico real se desejar
        proximas_notificacoes = calcular_proximas_notificacoes_programadas(
            documento.data_vencimento, prazos, enviados
        )

        return jsonify(
            {
                "id": documento.id,
                "nome": documento.nome,
                "tipo": documento.tipo.value,
                "tipo_personalizado": documento.tipo_personalizado,
                "data_emissao": documento.data_emissao.isoformat(),
                "data_vencimento": (
                    documento.data_vencimento.isoformat()
                    if documento.data_vencimento
                    else None
                ),
                "fazenda_id": documento.fazenda_id,
                "fazenda_nome": fazenda_nome,
                "fazenda_matricula": fazenda_matricula,
                "pessoa_id": documento.pessoa_id,
                "pessoa_nome": pessoa_nome,
                "emails_notificacao": documento.emails_notificacao,
                "prazos_notificacao": documento.prazos_notificacao,
                "esta_vencido": documento.esta_vencido,
                "proximo_vencimento": documento.proximo_vencimento,
                "proximas_notificacoes": proximas_notificacoes,
            }
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao obter documento {id}: {str(e)}")
        return (
            jsonify({"erro": f"Erro ao obter documento {id}", "detalhes": str(e)}),
            500,
        )

@documento_bp.route("/", methods=["POST"])
def criar_documento():
    """Cria um novo documento."""
    try:
        dados = request.form if request.form else request.json
        campos_obrigatorios = ["nome", "tipo", "data_emissao"]
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({"erro": f"Campo {campo} é obrigatório"}), 400

        try:
            tipo_documento = TipoDocumento(dados.get("tipo"))
        except ValueError:
            return jsonify({"erro": "Tipo de documento inválido"}), 400

        data_emissao = data_valida(dados.get("data_emissao"))
        if not data_emissao:
            return (
                jsonify({"erro": "Data de emissão inválida. Use o formato YYYY-MM-DD"}), 400
            )

        data_vencimento = None
        if dados.get("data_vencimento"):
            data_vencimento = data_valida(dados.get("data_vencimento"))
            if not data_vencimento:
                return (
                    jsonify({"erro": "Data de vencimento inválida. Use o formato YYYY-MM-DD"}), 400
                )

        fazenda_id = int(dados.get("fazenda_id")) if dados.get("fazenda_id") else None
        pessoa_id = int(dados.get("pessoa_id")) if dados.get("pessoa_id") else None

        # Validação opcional: se IDs forem passados, verifique existência
        if fazenda_id:
            fazenda = Fazenda.query.get(fazenda_id)
            if not fazenda:
                return jsonify({"erro": "Fazenda não encontrada"}), 404
        else:
            fazenda = None
        if pessoa_id:
            pessoa = Pessoa.query.get(pessoa_id)
            if not pessoa:
                return jsonify({"erro": "Pessoa não encontrada"}), 404
        else:
            pessoa = None

        prazos_notificacao = []
        prazo_notificacao = dados.get("prazo_notificacao", [])
        if prazo_notificacao:
            if hasattr(dados, "getlist"):
                for prazo in dados.getlist("prazo_notificacao[]"):
                    try:
                        prazos_notificacao.append(int(prazo))
                    except Exception:
                        return jsonify({"erro": "Prazo de notificação inválido"}), 400
            elif isinstance(prazo_notificacao, list):
                try:
                    prazos_notificacao = [int(p) for p in prazo_notificacao]
                except Exception:
                    return jsonify({"erro": "Prazo de notificação inválido"}), 400
            else:
                try:
                    prazos_notificacao = [int(prazo_notificacao)]
                except Exception:
                    return jsonify({"erro": "Prazo de notificação inválido"}), 400

        novo_documento = Documento(
            nome=dados.get("nome"),
            tipo=tipo_documento,
            tipo_personalizado=(
                dados.get("tipo_personalizado")
                if tipo_documento == TipoDocumento.OUTROS
                else None
            ),
            data_emissao=data_emissao,
            data_vencimento=data_vencimento,
            fazenda_id=fazenda_id,
            pessoa_id=pessoa_id
        )

        novo_documento.emails_notificacao = dados.get("emails_notificacao", "")
        novo_documento.prazos_notificacao = prazos_notificacao

        db.session.add(novo_documento)
        db.session.commit()

        fazenda_nome = fazenda.nome if fazenda else None
        fazenda_matricula = fazenda.matricula if fazenda else None
        pessoa_nome = pessoa.nome if pessoa else None

        return (
            jsonify(
                {
                    "id": novo_documento.id,
                    "nome": novo_documento.nome,
                    "tipo": novo_documento.tipo.value,
                    "data_emissao": novo_documento.data_emissao.isoformat(),
                    "data_vencimento": (
                        novo_documento.data_vencimento.isoformat()
                        if novo_documento.data_vencimento
                        else None
                    ),
                    "fazenda_id": novo_documento.fazenda_id,
                    "fazenda_nome": fazenda_nome,
                    "fazenda_matricula": fazenda_matricula,
                    "pessoa_id": novo_documento.pessoa_id,
                    "pessoa_nome": pessoa_nome,
                    "emails_notificacao": novo_documento.emails_notificacao,
                    "prazos_notificacao": novo_documento.prazos_notificacao,
                }
            ),
            201,
        )
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de integridade ao criar documento: {str(e)}")
        return (
            jsonify({"erro": "Erro de integridade no banco de dados", "detalhes": str(e)}), 400
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de banco de dados ao criar documento: {str(e)}")
        return jsonify({"erro": "Erro de banco de dados", "detalhes": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar documento: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"erro": "Erro ao criar documento", "detalhes": str(e)}), 500

@documento_bp.route("/<int:id>", methods=["PUT"])
def atualizar_documento(id):
    """Atualiza os dados de um documento existente."""
    try:
        documento = Documento.query.get_or_404(id)
        dados = request.form if request.form else request.json

        if not dados:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if dados.get("nome"):
            documento.nome = dados.get("nome")

        if dados.get("tipo"):
            try:
                documento.tipo = TipoDocumento(dados.get("tipo"))
                if documento.tipo == TipoDocumento.OUTROS and dados.get("tipo_personalizado"):
                    documento.tipo_personalizado = dados.get("tipo_personalizado")
            except ValueError:
                return jsonify({"erro": "Tipo de documento inválido"}), 400

        if dados.get("data_emissao"):
            data_emissao = data_valida(dados.get("data_emissao"))
            if not data_emissao:
                return jsonify({"erro": "Data de emissão inválida. Use o formato YYYY-MM-DD"}), 400
            documento.data_emissao = data_emissao

        if "data_vencimento" in dados:
            if dados.get("data_vencimento"):
                data_vencimento = data_valida(dados.get("data_vencimento"))
                if not data_vencimento:
                    return jsonify({"erro": "Data de vencimento inválida. Use o formato YYYY-MM-DD"}), 400
                documento.data_vencimento = data_vencimento
            else:
                documento.data_vencimento = None

        # Atualiza os relacionamentos
        if "fazenda_id" in dados:
            fazenda_id = int(dados.get("fazenda_id")) if dados.get("fazenda_id") else None
            if fazenda_id:
                fazenda = Fazenda.query.get(fazenda_id)
                if not fazenda:
                    return jsonify({"erro": "Fazenda não encontrada"}), 404
                documento.fazenda_id = fazenda_id
            else:
                documento.fazenda_id = None

        if "pessoa_id" in dados:
            pessoa_id = int(dados.get("pessoa_id")) if dados.get("pessoa_id") else None
            if pessoa_id:
                pessoa = Pessoa.query.get(pessoa_id)
                if not pessoa:
                    return jsonify({"erro": "Pessoa não encontrada"}), 404
                documento.pessoa_id = pessoa_id
            else:
                documento.pessoa_id = None

        if "emails_notificacao" in dados:
            documento.emails_notificacao = dados.get("emails_notificacao", "")

        prazo_notificacao = dados.get("prazo_notificacao", [])
        if prazo_notificacao:
            prazos_notificacao = []
            if hasattr(dados, "getlist"):
                for prazo in dados.getlist("prazo_notificacao[]"):
                    try:
                        prazos_notificacao.append(int(prazo))
                    except Exception:
                        return jsonify({"erro": "Prazo de notificação inválido"}), 400
                documento.prazos_notificacao = prazos_notificacao
            elif isinstance(prazo_notificacao, list):
                try:
                    documento.prazos_notificacao = [int(p) for p in prazo_notificacao]
                except Exception:
                    return jsonify({"erro": "Prazo de notificação inválido"}), 400
            else:
                try:
                    documento.prazos_notificacao = [int(prazo_notificacao)]
                except Exception:
                    return jsonify({"erro": "Prazo de notificação inválido"}), 400

        db.session.commit()

        fazenda_nome = documento.fazenda.nome if documento.fazenda else None
        fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
        pessoa_nome = documento.pessoa.nome if documento.pessoa else None

        return jsonify(
            {
                "id": documento.id,
                "nome": documento.nome,
                "tipo": documento.tipo.value,
                "tipo_personalizado": documento.tipo_personalizado,
                "data_emissao": documento.data_emissao.isoformat(),
                "data_vencimento": (
                    documento.data_vencimento.isoformat()
                    if documento.data_vencimento
                    else None
                ),
                "fazenda_id": documento.fazenda_id,
                "fazenda_nome": fazenda_nome,
                "fazenda_matricula": fazenda_matricula,
                "pessoa_id": documento.pessoa_id,
                "pessoa_nome": pessoa_nome,
                "emails_notificacao": documento.emails_notificacao,
                "prazos_notificacao": documento.prazos_notificacao,
            }
        )
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro de integridade ao atualizar documento {id}: {str(e)}"
        )
        return jsonify({"erro": "Erro de integridade no banco de dados", "detalhes": str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro de banco de dados ao atualizar documento {id}: {str(e)}"
        )
        return jsonify({"erro": "Erro de banco de dados", "detalhes": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro ao atualizar documento {id}: {str(e)}\n{traceback.format_exc()}"
        )
        return jsonify({"erro": "Erro ao atualizar documento", "detalhes": str(e)}), 500

@documento_bp.route("/<int:id>", methods=["DELETE"])
def excluir_documento(id):
    """Exclui um documento do sistema."""
    try:
        documento = Documento.query.get_or_404(id)
        nome = documento.nome

        db.session.delete(documento)
        db.session.commit()

        return jsonify({"mensagem": f"Documento {nome} excluído com sucesso"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro de banco de dados ao excluir documento {id}: {str(e)}"
        )
        return jsonify({"erro": "Erro de banco de dados ao excluir documento", "detalhes": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir documento {id}: {str(e)}")
        return jsonify({"erro": "Erro ao excluir documento", "detalhes": str(e)}), 500

@documento_bp.route("/vencidos", methods=["GET"])
def listar_documentos_vencidos():
    """API: Lista todos os documentos vencidos ou próximos do vencimento."""
    try:
        documentos = Documento.query.filter(Documento.data_vencimento.isnot(None)).all()
        vencidos = []
        proximos_vencimento = []

        for documento in documentos:
            fazenda_nome = documento.fazenda.nome if documento.fazenda else None
            fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
            pessoa_nome = documento.pessoa.nome if documento.pessoa else None

            if documento.esta_vencido:
                vencidos.append(
                    {
                        "id": documento.id,
                        "nome": documento.nome,
                        "tipo": documento.tipo.value,
                        "data_vencimento": documento.data_vencimento.isoformat(),
                        "fazenda_id": documento.fazenda_id,
                        "fazenda_nome": fazenda_nome,
                        "fazenda_matricula": fazenda_matricula,
                        "pessoa_id": documento.pessoa_id,
                        "pessoa_nome": pessoa_nome,
                        "emails_notificacao": documento.emails_notificacao,
                    }
                )
            elif documento.precisa_notificar:
                prazos = documento.prazos_notificacao if documento.prazos_notificacao else [30, 15, 7, 1]
                prazos = [int(p) for p in prazos]
                enviados = []  # Implemente se tiver histórico
                proximas_notificacoes = calcular_proximas_notificacoes_programadas(
                    documento.data_vencimento, prazos, enviados
                )
                proximos_vencimento.append(
                    {
                        "id": documento.id,
                        "nome": documento.nome,
                        "tipo": documento.tipo.value,
                        "data_vencimento": documento.data_vencimento.isoformat(),
                        "dias_restantes": documento.proximo_vencimento,
                        "fazenda_id": documento.fazenda_id,
                        "fazenda_nome": fazenda_nome,
                        "fazenda_matricula": fazenda_matricula,
                        "pessoa_id": documento.pessoa_id,
                        "pessoa_nome": pessoa_nome,
                        "emails_notificacao": documento.emails_notificacao,
                        "prazos_notificacao": documento.prazos_notificacao,
                        "proximas_notificacoes": proximas_notificacoes,
                    }
                )

        return jsonify(
            {"vencidos": vencidos, "proximos_vencimento": proximos_vencimento}
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao listar documentos vencidos: {str(e)}")
        return jsonify({"erro": "Erro ao listar documentos vencidos", "detalhes": str(e)}), 500

@documento_bp.route("/testar-email", methods=["POST"])
def testar_email():
    """Envia um e-mail de teste para verificar a configuração."""
    try:
        dados = request.form if request.form else request.json
        emails = dados.get("emails", "")

        if not emails:
            return jsonify({"sucesso": False, "mensagem": "Nenhum e-mail informado."}), 400

        lista_emails = [email.strip() for email in emails.split(",") if email.strip()]

        if not lista_emails:
            return jsonify({"sucesso": False, "mensagem": "Formato de e-mail inválido."}), 400

        sucesso, mensagem = enviar_email_teste(lista_emails)

        if sucesso:
            return jsonify({"sucesso": True, "mensagem": mensagem})
        else:
            return jsonify({"sucesso": False, "mensagem": mensagem}), 500
    except Exception as e:
        current_app.logger.error(f"Erro ao testar envio de e-mail: {str(e)}")
        return jsonify({"sucesso": False, "mensagem": f"Erro ao enviar e-mail de teste: {str(e)}"}, 500)

# -------- HTML VIEW ROUTE --------

@admin_documentos_bp.route("/vencidos")
def vencidos():
    """Rota HTML: Tela de documentos vencidos e próximos do vencimento."""
    documentos = Documento.query.filter(Documento.data_vencimento.isnot(None)).all()
    documentos_vencidos = []
    documentos_proximos = []

    for doc in documentos:
        if getattr(doc, "esta_vencido", False):
            documentos_vencidos.append(doc)
        elif getattr(doc, "precisa_notificar", False):
            prazos = doc.prazos_notificacao if doc.prazos_notificacao else [30, 15, 7, 1]
            prazos = [int(p) for p in prazos]
            enviados = []  # Implemente histórico se desejar
            doc.proximas_notificacoes = calcular_proximas_notificacoes_programadas(
                doc.data_vencimento, prazos, enviados
            )
            documentos_proximos.append(doc)

    return render_template(
        "admin/documentos/vencidos.html",
        documentos_vencidos=documentos_vencidos,
        documentos_proximos=documentos_proximos,
    )