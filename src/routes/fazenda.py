# /src/routes/fazenda.py

import traceback

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import NotFound

from src.models.db import db
from src.models.fazenda import Fazenda
from src.models.pessoa_fazenda import PessoaFazenda, TipoPosse  # Use o novo model intermediário

fazenda_bp = Blueprint("fazenda", __name__, url_prefix="/api/fazendas")


@fazenda_bp.route("/", methods=["GET"])
def listar_fazendas():
    """Lista todas as fazendas/áreas cadastradas."""
    try:
        fazendas = Fazenda.query.all()
        resultado = []

        for fazenda in fazendas:
            pessoas = [
                {
                    "id": pf.pessoa.id,
                    "nome": pf.pessoa.nome,
                    "tipo_posse": pf.tipo_posse.value,
                    "data_inicio": pf.data_inicio.isoformat() if pf.data_inicio else None,
                    "data_fim": pf.data_fim.isoformat() if pf.data_fim else None,
                }
                for pf in fazenda.pessoas_associadas
            ]
            resultado.append(
                {
                    "id": fazenda.id,
                    "nome": fazenda.nome,
                    "matricula": fazenda.matricula,
                    "tamanho_total": fazenda.tamanho_total,
                    "area_consolidada": fazenda.area_consolidada,
                    "tamanho_disponivel": fazenda.tamanho_disponivel,
                    "municipio": fazenda.municipio,
                    "estado": fazenda.estado,
                    "recibo_car": fazenda.recibo_car,
                    "pessoas": pessoas,
                }
            )

        return jsonify(resultado)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar fazendas: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"erro": "Erro ao listar fazendas", "detalhes": str(e)}), 500


@fazenda_bp.route("/<int:id>", methods=["GET"])
def obter_fazenda(id):
    """Obtém detalhes de uma fazenda/área específica."""
    try:
        fazenda = Fazenda.query.get_or_404(id)
        pessoas = [
            {
                "id": pf.pessoa.id,
                "nome": pf.pessoa.nome,
                "tipo_posse": pf.tipo_posse.value,
                "data_inicio": pf.data_inicio.isoformat() if pf.data_inicio else None,
                "data_fim": pf.data_fim.isoformat() if pf.data_fim else None,
            }
            for pf in fazenda.pessoas_associadas
        ]
        return jsonify(
            {
                "id": fazenda.id,
                "nome": fazenda.nome,
                "matricula": fazenda.matricula,
                "tamanho_total": fazenda.tamanho_total,
                "area_consolidada": fazenda.area_consolidada,
                "tamanho_disponivel": fazenda.tamanho_disponivel,
                "municipio": fazenda.municipio,
                "estado": fazenda.estado,
                "recibo_car": fazenda.recibo_car,
                "pessoas": pessoas,
            }
        )
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Erro de banco de dados ao obter fazenda {id}: {str(e)}\n{traceback.format_exc()}"
        )
        return (
            jsonify(
                {
                    "erro": f"Erro de banco de dados ao obter fazenda {id}",
                    "detalhes": str(e),
                }
            ),
            500,
        )


@fazenda_bp.route("/", methods=["POST"])
def criar_fazenda():
    """Cria uma nova fazenda/área e já associa pessoas (proprietário, arrendatário, etc)."""
    try:
        dados = request.json

        # Validação de campos obrigatórios
        campos_obrigatorios = [
            "nome",
            "matricula",
            "tamanho_total",
            "area_consolidada",
            "municipio",
            "estado",
        ]
        campos_faltantes = [
            campo for campo in campos_obrigatorios if campo not in dados
        ]

        if campos_faltantes:
            return (
                jsonify(
                    {
                        "erro": f'Campos obrigatórios não fornecidos: {", ".join(campos_faltantes)}'
                    }
                ),
                400,
            )

        # Verifica se já existe fazenda com a mesma matrícula
        if Fazenda.query.filter_by(matricula=dados.get("matricula")).first():
            return jsonify({"erro": "Matrícula já cadastrada para outra fazenda"}), 400

        # Validação dos tamanhos
        try:
            tamanho_total = float(dados.get("tamanho_total"))
            area_consolidada = float(dados.get("area_consolidada"))

            if tamanho_total <= 0:
                return jsonify({"erro": "Tamanho total deve ser maior que zero"}), 400

            if area_consolidada < 0:
                return jsonify({"erro": "Área consolidada não pode ser negativa"}), 400

            if area_consolidada > tamanho_total:
                return (
                    jsonify(
                        {
                            "erro": "Área consolidada não pode ser maior que o tamanho total"
                        }
                    ),
                    400,
                )

            tamanho_disponivel = tamanho_total - area_consolidada
        except ValueError:
            return jsonify({"erro": "Tamanhos devem ser valores numéricos"}), 400

        nova_fazenda = Fazenda(
            nome=dados.get("nome"),
            matricula=dados.get("matricula"),
            tamanho_total=tamanho_total,
            area_consolidada=area_consolidada,
            tamanho_disponivel=tamanho_disponivel,
            municipio=dados.get("municipio"),
            estado=dados.get("estado"),
            recibo_car=dados.get("recibo_car"),
        )

        db.session.add(nova_fazenda)
        db.session.flush()  # Para pegar o ID antes de criar vínculos

        # Criar vínculos de pessoa-fazenda no ato da criação, se enviados
        pessoas = dados.get("pessoas", [])
        for vinc in pessoas:
            pessoa_id = vinc.get("pessoa_id") or vinc.get("id")
            tipo_posse = vinc.get("tipo_posse")
            data_inicio = vinc.get("data_inicio")
            data_fim = vinc.get("data_fim")
            if pessoa_id and tipo_posse:
                pf = PessoaFazenda(
                    pessoa_id=pessoa_id,
                    fazenda_id=nova_fazenda.id,
                    tipo_posse=TipoPosse(tipo_posse),
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                )
                db.session.add(pf)

        db.session.commit()

        current_app.logger.info(
            f"Fazenda criada com sucesso: {nova_fazenda.nome} (ID: {nova_fazenda.id})"
        )

        return (
            jsonify(
                {
                    "id": nova_fazenda.id,
                    "nome": nova_fazenda.nome,
                    "matricula": nova_fazenda.matricula,
                    "tamanho_total": nova_fazenda.tamanho_total,
                    "area_consolidada": nova_fazenda.area_consolidada,
                    "tamanho_disponivel": nova_fazenda.tamanho_disponivel,
                    "municipio": nova_fazenda.municipio,
                    "estado": nova_fazenda.estado,
                    "recibo_car": nova_fazenda.recibo_car,
                }
            ),
            201,
        )
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de integridade ao criar fazenda: {str(e)}\n{traceback.format_exc()}")
        return (
            jsonify(
                {"erro": "Erro de integridade no banco de dados", "detalhes": str(e)}
            ),
            400,
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de banco de dados ao criar fazenda: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"erro": "Erro de banco de dados", "detalhes": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro ao criar fazenda: {str(e)}\n{traceback.format_exc()}"
        )
        return jsonify({"erro": "Erro ao criar fazenda", "detalhes": str(e)}), 500


@fazenda_bp.route("/<int:id>", methods=["PUT"])
def atualizar_fazenda(id):
    """Atualiza os dados de uma fazenda/área existente, inclusive vínculos de pessoas."""
    try:
        fazenda = Fazenda.query.get_or_404(id)
        dados = request.json

        if not dados:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        # Verifica se a matrícula já existe para outra fazenda
        if dados.get("matricula") and dados.get("matricula") != fazenda.matricula:
            fazenda_existente = Fazenda.query.filter_by(
                matricula=dados.get("matricula")
            ).first()
            if fazenda_existente and fazenda_existente.id != id:
                return (
                    jsonify({"erro": "Matrícula já cadastrada para outra fazenda"}),
                    400,
                )

        # Atualiza os campos
        if dados.get("nome"):
            fazenda.nome = dados.get("nome")
        if dados.get("matricula"):
            fazenda.matricula = dados.get("matricula")

        # Atualiza tamanhos se fornecidos
        if "tamanho_total" in dados or "area_consolidada" in dados:
            try:
                tamanho_total = float(dados.get("tamanho_total", fazenda.tamanho_total))
                area_consolidada = float(
                    dados.get("area_consolidada", fazenda.area_consolidada)
                )

                if tamanho_total <= 0:
                    return (
                        jsonify({"erro": "Tamanho total deve ser maior que zero"}),
                        400,
                    )

                if area_consolidada < 0:
                    return (
                        jsonify({"erro": "Área consolidada não pode ser negativa"}),
                        400,
                    )

                if area_consolidada > tamanho_total:
                    return (
                        jsonify(
                            {
                                "erro": "Área consolidada não pode ser maior que o tamanho total"
                            }
                        ),
                        400,
                    )

                fazenda.tamanho_total = tamanho_total
                fazenda.area_consolidada = area_consolidada
                fazenda.tamanho_disponivel = tamanho_total - area_consolidada
            except ValueError:
                return jsonify({"erro": "Tamanhos devem ser valores numéricos"}), 400

        # Atualiza outros campos
        if dados.get("municipio"):
            fazenda.municipio = dados.get("municipio")
        if dados.get("estado"):
            fazenda.estado = dados.get("estado")
        if "recibo_car" in dados:
            fazenda.recibo_car = dados.get("recibo_car")

        # Atualiza vínculos pessoa-fazenda: remove TODOS antigos e insere os recebidos
        if "pessoas" in dados:
            PessoaFazenda.query.filter_by(fazenda_id=fazenda.id).delete()
            pessoas = dados.get("pessoas", [])
            for vinc in pessoas:
                pessoa_id = vinc.get("pessoa_id") or vinc.get("id")
                tipo_posse = vinc.get("tipo_posse")
                data_inicio = vinc.get("data_inicio")
                data_fim = vinc.get("data_fim")
                if pessoa_id and tipo_posse:
                    pf = PessoaFazenda(
                        pessoa_id=pessoa_id,
                        fazenda_id=fazenda.id,
                        tipo_posse=TipoPosse(tipo_posse),
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                    )
                    db.session.add(pf)

        db.session.commit()

        current_app.logger.info(
            f"Fazenda atualizada com sucesso: {fazenda.nome} (ID: {fazenda.id})"
        )

        return jsonify(
            {
                "id": fazenda.id,
                "nome": fazenda.nome,
                "matricula": fazenda.matricula,
                "tamanho_total": fazenda.tamanho_total,
                "area_consolidada": fazenda.area_consolidada,
                "tamanho_disponivel": fazenda.tamanho_disponivel,
                "municipio": fazenda.municipio,
                "estado": fazenda.estado,
                "recibo_car": fazenda.recibo_car,
            }
        )
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro de integridade ao atualizar fazenda {id}: {str(e)}\n{traceback.format_exc()}"
        )
        return (
            jsonify(
                {"erro": "Erro de integridade no banco de dados", "detalhes": str(e)}
            ),
            400,
        )
    except NotFound as e:
        current_app.logger.error(
            f"Fazenda não encontrada ao atualizar fazenda {id}: {str(e)}\n{traceback.format_exc()}"
        )
        return jsonify({"erro": "Fazenda não encontrada", "detalhes": str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro de banco de dados ao atualizar fazenda {id}: {str(e)}\n{traceback.format_exc()}"
        )
        return jsonify({"erro": "Erro de banco de dados", "detalhes": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro ao atualizar fazenda {id}: {str(e)}\n{traceback.format_exc()}"
        )
        return jsonify({"erro": "Erro ao atualizar fazenda", "detalhes": str(e)}), 500


@fazenda_bp.route("/<int:id>", methods=["DELETE"])
def excluir_fazenda(id):
    """Exclui uma fazenda/área do sistema."""
    try:
        fazenda = Fazenda.query.get_or_404(id)

        # Verificar se a fazenda tem documentos associados
        if fazenda.documentos and len(fazenda.documentos) > 0:
            return (
                jsonify(
                    {
                        "erro": "Não é possível excluir a fazenda pois existem documentos associados a ela"
                    }
                ),
                400,
            )

        # Remover vínculos pessoa-fazenda (PessoaFazenda)
        PessoaFazenda.query.filter_by(fazenda_id=fazenda.id).delete()

        nome = fazenda.nome
        db.session.delete(fazenda)
        db.session.commit()

        current_app.logger.info(f"Fazenda excluída com sucesso: {nome} (ID: {id})")

        return jsonify({"mensagem": f"Fazenda {nome} excluída com sucesso"}), 200
    except NotFound as e:
        current_app.logger.error(
            f"Fazenda não encontrada ao excluir fazenda {id}: {str(e)}\n{traceback.format_exc()}"
        )
        return jsonify({"erro": "Fazenda não encontrada", "detalhes": str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erro de banco de dados ao excluir fazenda {id}: {str(e)}\n{traceback.format_exc()}"
        )
        return (
            jsonify(
                {
                    "erro": "Erro de banco de dados ao excluir fazenda",
                    "detalhes": str(e),
                }
            ),
            500,
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir fazenda {id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"erro": "Erro ao excluir fazenda", "detalhes": str(e)}), 500


@fazenda_bp.route("/<int:id>/pessoas", methods=["GET"])
def listar_pessoas_fazenda(id):
    """Lista todas as pessoas associadas a uma fazenda/área."""
    try:
        fazenda = Fazenda.query.get_or_404(id)
        pessoas = [
            {
                "id": pf.pessoa.id,
                "nome": pf.pessoa.nome,
                "cpf_cnpj": pf.pessoa.cpf_cnpj,
                "email": pf.pessoa.email,
                "telefone": pf.pessoa.telefone,
                "tipo_posse": pf.tipo_posse.value,
                "data_inicio": pf.data_inicio.isoformat() if pf.data_inicio else None,
                "data_fim": pf.data_fim.isoformat() if pf.data_fim else None,
            }
            for pf in fazenda.pessoas_associadas
        ]

        return jsonify(pessoas)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar pessoas da fazenda {id}: {str(e)}\n{traceback.format_exc()}")
        return (
            jsonify(
                {"erro": f"Erro ao listar pessoas da fazenda {id}", "detalhes": str(e)}
            ),
            500,
        )


@fazenda_bp.route("/<int:id>/documentos", methods=["GET"])
def listar_documentos_fazenda(id):
    """Lista todos os documentos associados a uma fazenda/área."""
    try:
        fazenda = Fazenda.query.get_or_404(id)
        documentos = []

        for documento in fazenda.documentos:
            documentos.append(
                {
                    "id": documento.id,
                    "nome": documento.nome,
                    "tipo": documento.tipo.value,
                    "data_emissao": documento.data_emissao.isoformat(),
                    "data_vencimento": (
                        documento.data_vencimento.isoformat()
                        if documento.data_vencimento
                        else None
                    ),
                    "emails_notificacao": documento.emails_notificacao,
                    "prazos_notificacao": documento.prazos_notificacao,
                    "esta_vencido": getattr(documento, "esta_vencido", False),
                    "proximo_vencimento": getattr(documento, "proximo_vencimento", None),
                }
            )

        return jsonify(documentos)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar documentos da fazenda {id}: {str(e)}\n{traceback.format_exc()}")
        return (
            jsonify(
                {
                    "erro": f"Erro ao listar documentos da fazenda {id}",
                    "detalhes": str(e),
                }
            ),
            500,
        )