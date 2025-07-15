# /src/routes/endividamento.py

import json
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import and_, or_

from src.forms.endividamento import EndividamentoForm, FiltroEndividamentoForm
from src.forms.notificacao_endividamento import NotificacaoEndividamentoForm
from src.models.db import db
from src.models.endividamento import Endividamento, EndividamentoFazenda, Parcela
from src.models.fazenda import Fazenda
from src.models.notificacao_endividamento import NotificacaoEndividamento
from src.models.pessoa import Pessoa
from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
from src.utils.validators import sanitize_input
from src.utils.notificacao_utils import calcular_proximas_notificacoes_programadas

# IMPORTS PARA ÁREAS VINCULADAS AO ENDIVIDAMENTO
from src.utils.endividamento_area_utils import (
    adicionar_areas_endividamento,
    get_areas_vinculadas,
    remover_area_vinculo,
    validar_hectares_disponiveis
)

endividamento_bp = Blueprint("endividamento", __name__, url_prefix="/endividamentos")

# --- CRUD ÁREAS VINCULADAS AO ENDIVIDAMENTO (API) ---

@endividamento_bp.route("/<int:id>/areas", methods=["POST"])
def add_areas_endividamento(id):
    """
    Vincula áreas a um endividamento.
    Espera JSON: {"areas": [{"area_id":..., "tipo":..., "hectares_utilizados":...}, ...]}
    """
    data = request.get_json()
    for area in data['areas']:
        if area.get('hectares_utilizados'):
            ok, msg = validar_hectares_disponiveis(area['area_id'], area['hectares_utilizados'])
            if not ok:
                return jsonify({'error': msg}), 400
    adicionar_areas_endividamento(id, data['areas'])
    return jsonify({"message": "Áreas vinculadas com sucesso."}), 201

@endividamento_bp.route("/<int:id>/areas", methods=["GET"])
def listar_areas_endividamento(id):
    """
    Lista áreas vinculadas a um endividamento.
    """
    areas = get_areas_vinculadas(id)
    return jsonify(areas), 200

@endividamento_bp.route("/<int:endividamento_id>/area/<int:area_id>", methods=["DELETE"])
def desvincular_area(endividamento_id, area_id):
    """
    Desvincula uma área de um endividamento.
    """
    remover_area_vinculo(endividamento_id, area_id)
    return jsonify({"message": "Área desvinculada com sucesso."}), 200

# --- RESTANTE DAS ROTAS DO ENDIVIDAMENTO ---

@endividamento_bp.route("/")
def listar():
    """Lista todos os endividamentos com filtros opcionais"""
    form_filtro = FiltroEndividamentoForm()

    # Preencher opções dos selects
    form_filtro.pessoa_id.choices = [(0, "Todas as pessoas")] + [
        (p.id, p.nome) for p in Pessoa.query.all()
    ]
    form_filtro.fazenda_id.choices = [(0, "Todas as fazendas")] + [
        (f.id, f.nome) for f in Fazenda.query.all()
    ]

    query = Endividamento.query

    if request.args.get("banco"):
        query = query.filter(
            Endividamento.banco.ilike(f"%{request.args.get('banco')}%")
        )

    if request.args.get("pessoa_id") and int(request.args.get("pessoa_id")) > 0:
        query = query.join(Endividamento.pessoas).filter(
            Pessoa.id == int(request.args.get("pessoa_id"))
        )

    if request.args.get("fazenda_id") and int(request.args.get("fazenda_id")) > 0:
        query = query.join(Endividamento.fazenda_vinculos).filter(
            EndividamentoFazenda.fazenda_id == int(request.args.get("fazenda_id"))
        )

    if request.args.get("data_inicio"):
        data_inicio = datetime.strptime(
            request.args.get("data_inicio"), "%Y-%m-%d"
        ).date()
        query = query.filter(Endividamento.data_emissao >= data_inicio)

    if request.args.get("data_fim"):
        data_fim = datetime.strptime(request.args.get("data_fim"), "%Y-%m-%d").date()
        query = query.filter(Endividamento.data_emissao <= data_fim)

    if request.args.get("vencimento_inicio"):
        venc_inicio = datetime.strptime(
            request.args.get("vencimento_inicio"), "%Y-%m-%d"
        ).date()
        query = query.filter(Endividamento.data_vencimento_final >= venc_inicio)

    if request.args.get("vencimento_fim"):
        venc_fim = datetime.strptime(
            request.args.get("vencimento_fim"), "%Y-%m-%d"
        ).date()
        query = query.filter(Endividamento.data_vencimento_final <= venc_fim)

    endividamentos = query.order_by(Endividamento.data_vencimento_final.asc()).all()

    return render_template(
        "admin/endividamentos/listar.html",
        endividamentos=endividamentos,
        form_filtro=form_filtro,
        date=date,
    )

@endividamento_bp.route("/novo", methods=["GET", "POST"])
def novo():
    """Cadastra um novo endividamento"""
    form = EndividamentoForm()

    if request.method == "POST":
        if form.validate_on_submit():
            try:
                endividamento = Endividamento(
                    banco=sanitize_input(form.banco.data),
                    numero_proposta=sanitize_input(form.numero_proposta.data),
                    data_emissao=form.data_emissao.data,
                    data_vencimento_final=form.data_vencimento_final.data,
                    taxa_juros=form.taxa_juros.data,
                    tipo_taxa_juros=form.tipo_taxa_juros.data,
                    prazo_carencia=form.prazo_carencia.data,
                    valor_operacao=form.valor_operacao.data,
                )

                db.session.add(endividamento)
                db.session.flush()  # Para obter o ID

                # Processar pessoas selecionadas
                pessoas_ids = request.form.getlist("pessoas_ids")
                if pessoas_ids:
                    pessoas = Pessoa.query.filter(Pessoa.id.in_(pessoas_ids)).all()
                    endividamento.pessoas = pessoas

                # Processar vínculos com fazendas (objeto do crédito)
                objetos_credito = json.loads(request.form.get("objetos_credito") or "[]")
                for obj in objetos_credito:
                    if obj.get("fazenda_id") and obj.get("hectares"):
                        vinculo = EndividamentoFazenda(
                            endividamento_id=endividamento.id,
                            fazenda_id=int(obj["fazenda_id"]),
                            hectares=float(obj["hectares"]),
                            tipo="objeto_credito",
                            descricao=sanitize_input(obj.get("descricao")),
                        )
                        db.session.add(vinculo)

                # Processar garantias
                garantias = json.loads(request.form.get("garantias") or "[]")
                for gar in garantias:
                    if gar.get("fazenda_id"):
                        vinculo = EndividamentoFazenda(
                            endividamento_id=endividamento.id,
                            fazenda_id=int(gar["fazenda_id"]),
                            hectares=None,
                            tipo="garantia",
                            descricao=sanitize_input(gar.get("descricao")),
                        )
                        db.session.add(vinculo)

                # Processar parcelas
                parcelas = json.loads(request.form.get("parcelas") or "[]")
                for parc in parcelas:
                    if parc.get("data_vencimento") and parc.get("valor"):
                        parcela = Parcela(
                            endividamento_id=endividamento.id,
                            data_vencimento=datetime.strptime(
                                parc["data_vencimento"], "%Y-%m-%d"
                            ).date(),
                            valor=float(parc["valor"]),
                        )
                        db.session.add(parcela)

                db.session.commit()
                flash("Endividamento cadastrado com sucesso!", "success")
                return redirect(url_for("endividamento.listar"))

            except Exception as e:
                db.session.rollback()
                flash(f"Erro ao cadastrar endividamento: {str(e)}", "danger")
        else:
            flash(
                "Erro na validação do formulário. Verifique os dados informados.",
                "danger",
            )

    pessoas = Pessoa.query.all()
    fazendas = Fazenda.query.all()

    return render_template(
        "admin/endividamentos/form.html",
        form=form,
        pessoas=pessoas,
        fazendas=fazendas,
        endividamento=None,
    )

@endividamento_bp.route("/<int:id>")
def visualizar(id):
    """Visualiza detalhes de um endividamento"""
    endividamento = Endividamento.query.get_or_404(id)

    # Obter configuração de notificação
    config = NotificacaoEndividamento.query.filter_by(endividamento_id=id, ativo=True).first()
    prazos = [30, 15, 7, 1]
    if config and hasattr(config, "prazos") and config.prazos:
        try:
            prazos = json.loads(config.prazos)
        except Exception:
            pass

    # Já enviadas?
    from src.models.notificacao_endividamento import HistoricoNotificacao
    enviados = [
        n.tipo_notificacao for n in HistoricoNotificacao.query.filter_by(endividamento_id=id, sucesso=True)
    ]
    proximas_notificacoes = calcular_proximas_notificacoes_programadas(
        endividamento.data_vencimento_final, prazos, enviados
    )

    # Áreas vinculadas via utilitário
    areas_vinculadas = get_areas_vinculadas(endividamento.id)

    return render_template(
        "admin/endividamentos/visualizar.html",
        endividamento=endividamento,
        date=date,
        proximas_notificacoes=proximas_notificacoes,
        areas_vinculadas=areas_vinculadas,
    )

@endividamento_bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    """Edita um endividamento existente"""
    endividamento = Endividamento.query.get_or_404(id)
    form = EndividamentoForm(obj=endividamento)

    if request.method == "POST":
        if form.validate_on_submit():
            try:
                endividamento.banco = sanitize_input(form.banco.data)
                endividamento.numero_proposta = sanitize_input(
                    form.numero_proposta.data
                )
                endividamento.data_emissao = form.data_emissao.data
                endividamento.data_vencimento_final = form.data_vencimento_final.data
                endividamento.taxa_juros = form.taxa_juros.data
                endividamento.tipo_taxa_juros = form.tipo_taxa_juros.data
                endividamento.prazo_carencia = form.prazo_carencia.data
                endividamento.valor_operacao = form.valor_operacao.data

                pessoas_ids = request.form.getlist("pessoas_ids")
                if pessoas_ids:
                    pessoas = Pessoa.query.filter(Pessoa.id.in_(pessoas_ids)).all()
                    endividamento.pessoas = pessoas
                else:
                    endividamento.pessoas = []

                EndividamentoFazenda.query.filter_by(endividamento_id=id).delete()

                objetos_credito = json.loads(request.form.get("objetos_credito") or "[]")
                for obj in objetos_credito:
                    if obj.get("fazenda_id") and obj.get("hectares"):
                        vinculo = EndividamentoFazenda(
                            endividamento_id=endividamento.id,
                            fazenda_id=int(obj["fazenda_id"]),
                            hectares=float(obj["hectares"]),
                            tipo="objeto_credito",
                            descricao=sanitize_input(obj.get("descricao")),
                        )
                        db.session.add(vinculo)

                garantias = json.loads(request.form.get("garantias") or "[]")
                for gar in garantias:
                    if gar.get("fazenda_id"):
                        vinculo = EndividamentoFazenda(
                            endividamento_id=endividamento.id,
                            fazenda_id=int(gar["fazenda_id"]),
                            hectares=None,
                            tipo="garantia",
                            descricao=sanitize_input(gar.get("descricao")),
                        )
                        db.session.add(vinculo)

                Parcela.query.filter_by(endividamento_id=id).delete()

                parcelas = json.loads(request.form.get("parcelas") or "[]")
                for parc in parcelas:
                    if parc.get("data_vencimento") and parc.get("valor"):
                        parcela = Parcela(
                            endividamento_id=endividamento.id,
                            data_vencimento=datetime.strptime(
                                parc["data_vencimento"], "%Y-%m-%d"
                            ).date(),
                            valor=float(parc["valor"]),
                        )
                        db.session.add(parcela)

                db.session.commit()
                flash("Endividamento atualizado com sucesso!", "success")
                return redirect(url_for("endividamento.visualizar", id=id))

            except Exception as e:
                db.session.rollback()
                flash(f"Erro ao atualizar endividamento: {str(e)}", "danger")
        else:
            flash(
                "Erro na validação do formulário. Verifique os dados informados.",
                "danger",
            )

    pessoas = Pessoa.query.all()
    fazendas = Fazenda.query.all()

    return render_template(
        "admin/endividamentos/form.html",
        form=form,
        pessoas=pessoas,
        fazendas=fazendas,
        endividamento=endividamento,
    )

@endividamento_bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    """Exclui um endividamento"""
    endividamento = Endividamento.query.get_or_404(id)

    try:
        db.session.delete(endividamento)
        db.session.commit()
        flash("Endividamento excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir endividamento: {str(e)}", "danger")

    return redirect(url_for("endividamento.listar"))

@endividamento_bp.route("/vencimentos")
def vencimentos():
    """Lista parcelas próximas do vencimento e exibe próximas notificações programadas"""
    hoje = date.today()

    parcelas_vencidas = (
        Parcela.query.filter(Parcela.data_vencimento < hoje, Parcela.pago.is_(False))
        .order_by(Parcela.data_vencimento.asc())
        .all()
    )

    data_limite = hoje + timedelta(days=30)

    parcelas_a_vencer = (
        Parcela.query.filter(
            and_(
                Parcela.data_vencimento >= hoje,
                Parcela.data_vencimento <= data_limite,
                Parcela.pago.is_(False),
            )
        )
        .order_by(Parcela.data_vencimento.asc())
        .all()
    )

    # Adiciona próximas notificações programadas a cada parcela (baseado no endividamento da parcela)
    from src.models.notificacao_endividamento import HistoricoNotificacao

    for parcela in parcelas_a_vencer:
        endividamento = parcela.endividamento
        config = NotificacaoEndividamento.query.filter_by(endividamento_id=endividamento.id, ativo=True).first()
        prazos = [30, 15, 7, 1]
        if config and hasattr(config, "prazos") and config.prazos:
            try:
                prazos = json.loads(config.prazos)
            except Exception:
                pass
        enviados = [
            n.tipo_notificacao for n in HistoricoNotificacao.query.filter_by(endividamento_id=endividamento.id, sucesso=True)
        ]
        parcela.proximas_notificacoes = calcular_proximas_notificacoes_programadas(
            endividamento.data_vencimento_final, prazos, enviados
        )

    return render_template(
        "admin/endividamentos/vencimentos.html",
        parcelas_vencidas=parcelas_vencidas,
        parcelas_a_vencer=parcelas_a_vencer,
        date=date,
    )

@endividamento_bp.route("/parcela/<int:id>/pagar", methods=["POST"])
def pagar_parcela(id):
    """Marca uma parcela como paga"""
    parcela = Parcela.query.get_or_404(id)

    try:
        parcela.pago = True
        parcela.data_pagamento = date.today()
        parcela.valor_pago = request.form.get("valor_pago", parcela.valor)
        parcela.observacoes = sanitize_input(request.form.get("observacoes", ""))

        db.session.commit()
        flash("Parcela marcada como paga!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao marcar parcela como paga: {str(e)}", "danger")

    return redirect(url_for("endividamento.vencimentos"))

@endividamento_bp.route("/api/fazendas/<int:pessoa_id>")
def api_fazendas_pessoa(pessoa_id):
    """API para obter fazendas de uma pessoa"""
    pessoa = Pessoa.query.get_or_404(pessoa_id)
    fazendas = [
        {"id": f.id, "nome": f.nome, "tamanho_total": float(f.tamanho_total)}
        for f in pessoa.fazendas
    ]
    return jsonify(fazendas)

@endividamento_bp.route("/buscar-pessoas")
def buscar_pessoas():
    """Endpoint para busca AJAX de pessoas com cache Redis e paginação"""
    from src.utils.cache import cache

    termo = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)

    if len(termo) < 2:
        return jsonify([])

    page = max(1, page)
    limit = min(max(1, limit), 50)

    cache_key = f"buscar_pessoas:{termo}:{page}:{limit}"

    resultado_cache = cache.get(cache_key)
    if resultado_cache is not None:
        return jsonify(resultado_cache)

    offset = (page - 1) * limit

    query = Pessoa.query.filter(
        or_(Pessoa.nome.ilike(f"%{termo}%"), Pessoa.cpf_cnpj.ilike(f"%{termo}%"))
    )

    total_count = query.count()
    pessoas = query.offset(offset).limit(limit).all()

    resultado = [
        {
            "id": pessoa.id,
            "nome": pessoa.nome,
            "cpf_cnpj": pessoa.cpf_cnpj,
            "cpf_cnpj_formatado": pessoa.formatar_cpf_cnpj(),
        }
        for pessoa in pessoas
    ]

    response_data = resultado
    if "page" in request.args or "limit" in request.args:
        response_data = {
            "data": resultado,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "has_next": offset + limit < total_count,
                "has_prev": page > 1,
                "total_pages": (total_count + limit - 1) // limit
            }
        }

    cache.set(cache_key, response_data, timeout=300)

    return jsonify(response_data)

@endividamento_bp.route("/<int:id>/notificacoes", methods=["GET", "POST"])
def configurar_notificacoes(id):
    """Configura notificações para um endividamento"""
    endividamento = Endividamento.query.get_or_404(id)
    form = NotificacaoEndividamentoForm()
    service = NotificacaoEndividamentoService()

    if request.method == "POST":
        if form.validate_on_submit():
            try:
                emails = [
                    email.strip()
                    for email in form.emails.data.split("\n")
                    if email.strip()
                ]

                sucesso = service.configurar_notificacao(
                    endividamento_id=id, emails=emails, ativo=form.ativo.data
                )

                if sucesso:
                    flash("Configurações de notificação salvas com sucesso!", "success")
                    return redirect(url_for("endividamento.visualizar", id=id))
                else:
                    flash("Erro ao salvar configurações de notificação.", "danger")

            except Exception as e:
                flash(f"Erro ao processar configurações: {str(e)}", "danger")
        else:
            flash(
                "Erro na validação do formulário. Verifique os dados informados.",
                "danger",
            )

    configuracao = service.obter_configuracao(id)
    if configuracao["emails"]:
        form.emails.data = "\n".join(configuracao["emails"])
        form.ativo.data = configuracao["ativo"]

    historico = service.obter_historico(id)

    return render_template(
        "admin/endividamentos/notificacoes.html",
        endividamento=endividamento,
        form=form,
        historico=historico,
    )

@endividamento_bp.route("/api/processar-notificacoes", methods=["POST"])
def processar_notificacoes():
    """API para processar notificações manualmente (para testes)"""
    try:
        service = NotificacaoEndividamentoService()
        notificacoes_enviadas = service.verificar_e_enviar_notificacoes()

        return jsonify(
            {
                "sucesso": True,
                "notificacoes_enviadas": notificacoes_enviadas,
                "mensagem": f"{notificacoes_enviadas} notificações foram enviadas.",
            }
        )

    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500