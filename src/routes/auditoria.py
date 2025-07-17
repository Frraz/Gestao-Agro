# /src/routes/auditoria.py

import json
from urllib.parse import urlencode

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import or_

from src.models.auditoria import Auditoria
from src.models.db import db
from src.models.fazenda import Fazenda
from src.models.pessoa import Pessoa

auditoria_bp = Blueprint("auditoria", __name__)

# Função auxiliar para paginação no template (preserva filtros)
@auditoria_bp.app_template_global()
def url_for_other_page(page):
    args = request.args.copy()
    args = args.to_dict(flat=False)
    args['page'] = [str(page)]
    return f"{request.path}?{urlencode(args, doseq=True)}"

@auditoria_bp.route("/admin/auditoria")
@login_required
def painel_auditoria():
    """Painel de logs de auditoria, com filtros avançados."""

    query = Auditoria.query

    data_ini = request.args.get("data_ini")
    data_fim = request.args.get("data_fim")
    usuario = request.args.get("usuario")
    entidade = request.args.get("entidade")
    acao = request.args.get("acao")
    nome_fazenda = request.args.get("nome_fazenda")
    nome_pessoa = request.args.get("nome_pessoa")

    if data_ini:
        query = query.filter(Auditoria.data_hora >= data_ini)
    if data_fim:
        query = query.filter(Auditoria.data_hora <= data_fim + " 23:59:59")
    if usuario:
        # O join pode não ser necessário dependendo do relacionamento; mantenha se existir relacionamento.
        query = query.filter(Auditoria.usuario_nome == usuario) if hasattr(Auditoria, "usuario_nome") else query

    if entidade:
        query = query.filter(Auditoria.entidade == entidade)
    if acao:
        query = query.filter(Auditoria.acao == acao)

    # Filtro por nome da fazenda (pesquisa em valor_novo e valor_anterior)
    if nome_fazenda:
        fazendas_ids = [
            f.id
            for f in Fazenda.query.filter(Fazenda.nome.ilike(f"%{nome_fazenda}%")).all()
        ]
        if fazendas_ids:
            query = query.filter(
                or_(
                    *[
                        Auditoria.valor_novo.contains(str(fid)) | Auditoria.valor_anterior.contains(str(fid))
                        for fid in fazendas_ids
                    ]
                )
            )

    # Filtro por nome da pessoa (pesquisa em valor_novo e valor_anterior)
    if nome_pessoa:
        pessoas_ids = [
            p.id
            for p in Pessoa.query.filter(Pessoa.nome.ilike(f"%{nome_pessoa}%")).all()
        ]
        if pessoas_ids:
            query = query.filter(
                or_(
                    *[
                        Auditoria.valor_novo.contains(str(pid)) | Auditoria.valor_anterior.contains(str(pid))
                        for pid in pessoas_ids
                    ]
                )
            )

    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = query.order_by(Auditoria.data_hora.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    # Pré-carregar todas as fazendas e pessoas em dicionários para evitar N+1 queries
    fazendas = {f.id: f.nome for f in Fazenda.query.all()}
    pessoas = {p.id: p.nome for p in Pessoa.query.all()}

    def extrair_identificacao(log):
        valor = {}
        for v in (log.valor_novo, log.valor_anterior):
            if v:
                try:
                    valor = json.loads(v)
                    break
                except Exception:
                    pass
        if log.entidade == "Documento":
            return valor.get("nome", f"ID {valor.get('id', '-')}")
        if log.entidade == "Pessoa":
            return valor.get("nome", valor.get("cpf_cnpj", "-"))
        if log.entidade == "Fazenda":
            return valor.get("nome", f"ID {valor.get('id', '-')}")
        if log.entidade == "PessoaFazenda":
            return f"Pessoa {valor.get('pessoa_id', '')} - Fazenda {valor.get('fazenda_id', '')}"
        return "-"

    def extrair_associado(log):
        valor = {}
        for v in (log.valor_novo, log.valor_anterior):
            if v:
                try:
                    valor = json.loads(v)
                    break
                except Exception:
                    pass
        if log.entidade == "Documento":
            if valor.get("pessoa_id"):
                nome = pessoas.get(valor["pessoa_id"], str(valor["pessoa_id"]))
                return f"Pessoa: {nome}"
            elif valor.get("fazenda_id"):
                nome = fazendas.get(valor["fazenda_id"], str(valor["fazenda_id"]))
                return f"Fazenda: {nome}"
        if log.entidade == "Pessoa":
            if valor.get("fazenda_id"):
                nome = fazendas.get(valor["fazenda_id"], str(valor["fazenda_id"]))
                return f"Fazenda: {nome}"
        if log.entidade == "PessoaFazenda":
            nome_p = pessoas.get(valor.get("pessoa_id"), str(valor.get("pessoa_id")))
            nome_f = fazendas.get(valor.get("fazenda_id"), str(valor.get("fazenda_id")))
            return f"Pessoa: {nome_p}, Fazenda: {nome_f}, Tipo Posse: {valor.get('tipo_posse')}"
        return "-"

    for log in logs:
        log.identificacao = extrair_identificacao(log)
        log.associado = extrair_associado(log)

    # Resposta AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("admin/_auditoria_table.html", logs=logs, pagination=pagination)
    return render_template("admin/auditoria.html", logs=logs, pagination=pagination)