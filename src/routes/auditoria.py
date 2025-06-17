#/src/routes/auditoria.py

from flask import Blueprint, render_template, request
from src.models.auditoria import Auditoria
from flask_login import login_required
from src.models.fazenda import Fazenda
from src.models.pessoa import Pessoa
from src.models.db import db
import json

auditoria_bp = Blueprint('auditoria', __name__)

@auditoria_bp.route('/admin/auditoria')
@login_required
def painel_auditoria():
    # Filtros
    query = Auditoria.query

    data_ini = request.args.get('data_ini')
    data_fim = request.args.get('data_fim')
    usuario = request.args.get('usuario')
    entidade = request.args.get('entidade')
    acao = request.args.get('acao')
    nome_fazenda = request.args.get('nome_fazenda')
    nome_pessoa = request.args.get('nome_pessoa')

    if data_ini:
        query = query.filter(Auditoria.data_hora >= data_ini)
    if data_fim:
        query = query.filter(Auditoria.data_hora <= data_fim + " 23:59:59")
    if usuario:
        query = query.join(Auditoria.usuario).filter(Auditoria.usuario.has(nome=usuario))
    if entidade:
        query = query.filter(Auditoria.entidade == entidade)
    if acao:
        query = query.filter(Auditoria.acao == acao)

    # --- Filtro por nome da fazenda ---
    if nome_fazenda:
        fazendas_ids = [f.id for f in Fazenda.query.filter(Fazenda.nome.ilike(f"%{nome_fazenda}%")).all()]
        if fazendas_ids:
            query = query.filter(
                db.or_(
                    *[(Auditoria.valor_novo.contains(str(fid)) | Auditoria.valor_anterior.contains(str(fid))) for fid in fazendas_ids]
                )
            )

    # --- Filtro por nome da pessoa ---
    if nome_pessoa:
        pessoas_ids = [p.id for p in Pessoa.query.filter(Pessoa.nome.ilike(f"%{nome_pessoa}%")).all()]
        if pessoas_ids:
            query = query.filter(
                db.or_(
                    *[(Auditoria.valor_novo.contains(str(pid)) | Auditoria.valor_anterior.contains(str(pid))) for pid in pessoas_ids]
                )
            )

    logs = query.order_by(Auditoria.data_hora.desc()).limit(100).all()

    # Pré-carregar todas as fazendas e pessoas em dicionários para evitar N+1 queries
    fazendas = {f.id: f.nome for f in Fazenda.query.all()}
    pessoas = {p.id: p.nome for p in Pessoa.query.all()}

    def extrair_identificacao(log):
        try:
            valor = json.loads(log.valor_novo or log.valor_anterior or '{}')
        except Exception:
            valor = {}
        if log.entidade == 'Documento':
            return valor.get('nome', f"ID {valor.get('id', '-')}")
        if log.entidade == 'Pessoa':
            return valor.get('nome', valor.get('cpf_cnpj', '-'))
        if log.entidade == 'Fazenda':
            return valor.get('nome', f"ID {valor.get('id', '-')}")
        return '-'

    def extrair_associado(log):
        try:
            valor = json.loads(log.valor_novo or log.valor_anterior or '{}')
        except Exception:
            valor = {}
        if log.entidade == 'Documento':
            if valor.get('pessoa_id'):
                nome = pessoas.get(valor['pessoa_id'], str(valor['pessoa_id']))
                return f"Pessoa: {nome}"
            elif valor.get('fazenda_id'):
                nome = fazendas.get(valor['fazenda_id'], str(valor['fazenda_id']))
                return f"Fazenda: {nome}"
        if log.entidade == 'Pessoa':
            if valor.get('fazenda_id'):
                nome = fazendas.get(valor['fazenda_id'], str(valor['fazenda_id']))
                return f"Fazenda: {nome}"
        return '-'

    for log in logs:
        log.identificacao = extrair_identificacao(log)
        log.associado = extrair_associado(log)

    return render_template('admin/auditoria.html', logs=logs)