# /src/routes/admin.py

"""
Rotas administrativas para o Sistema de Gestão de Fazendas.

Inclui:
- Dashboard com documentos vencidos e próximos do vencimento
- CRUD de Pessoas e Fazendas, incluindo associação/desassociação
- CRUD de Documentos
- Notificações de vencimento
- Integração com Flask-Login e auditoria
"""

import datetime
from datetime import date
from math import ceil

from flask import (
    Blueprint, flash, jsonify, redirect, render_template,
    request, url_for
)
from flask_login import login_required

from src.utils.notificacao_utils import calcular_proximas_notificacoes_programadas
from src.models.db import db
from src.models.documento import Documento, TipoDocumento
from src.models.fazenda import Fazenda
from src.models.pessoa import Pessoa
from src.models.pessoa_fazenda import TipoPosse
from src.utils.auditoria import registrar_auditoria
from src.utils.email_service import (
    EmailService, formatar_email_notificacao, verificar_documentos_vencendo
)
from src.forms.pessoa import PessoaForm

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# ---------------- Dashboard ----------------

@admin_bp.route("/")
@login_required
def index():
    """Página inicial do painel administrativo."""
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    hoje = date.today()
    prox_page = request.args.get("prox_page", type=int, default=1)
    venc_page = request.args.get("venc_page", type=int, default=1)
    per_page = 10

    docs_proximos_query = Documento.query.filter(
        Documento.data_vencimento >= hoje
    ).order_by(Documento.data_vencimento.asc())
    total_proximos = docs_proximos_query.count()
    docs_proximos = (
        docs_proximos_query.offset((prox_page - 1) * per_page).limit(per_page).all()
    )
    total_pag_proximos = ceil(total_proximos / per_page) if total_proximos else 1

    docs_vencidos_query = Documento.query.filter(
        Documento.data_vencimento < hoje
    ).order_by(Documento.data_vencimento.asc())
    total_vencidos = docs_vencidos_query.count()
    docs_vencidos = (
        docs_vencidos_query.offset((venc_page - 1) * per_page).limit(per_page).all()
    )
    total_pag_vencidos = ceil(total_vencidos / per_page) if total_vencidos else 1

    total_pessoas = Pessoa.query.count()
    total_fazendas = Fazenda.query.count()
    total_documentos = Documento.query.count()

    return render_template(
        "admin/index.html",
        total_pessoas=total_pessoas,
        total_fazendas=total_fazendas,
        total_documentos=total_documentos,
        documentos_proximos=docs_proximos,
        documentos_vencidos=docs_vencidos,
        prox_page=prox_page,
        total_pag_proximos=total_pag_proximos,
        venc_page=venc_page,
        total_pag_vencidos=total_pag_vencidos,
    )

# ---------------- Pessoas ----------------

@admin_bp.route("/pessoas")
@login_required
def listar_pessoas():
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    return render_template("admin/pessoas/listar.html", pessoas=pessoas)

@admin_bp.route("/pessoas/nova", methods=["GET", "POST"])
@login_required
def nova_pessoa():
    form = PessoaForm()
    if form.validate_on_submit():
        pessoa_existente = Pessoa.query.filter_by(cpf_cnpj=form.cpf_cnpj.data.strip()).first()
        if pessoa_existente:
            flash(f"Já existe uma pessoa cadastrada com o CPF/CNPJ {form.cpf_cnpj.data.strip()}.", "danger")
            return render_template("admin/pessoas/form.html", form=form)
        nova_pessoa = Pessoa(
            nome=form.nome.data.strip(),
            cpf_cnpj=form.cpf_cnpj.data.strip(),
            email=form.email.data.strip(),
            telefone=form.telefone.data.strip(),
            endereco=form.endereco.data.strip(),
        )
        db.session.add(nova_pessoa)
        db.session.commit()
        registrar_auditoria(
            acao="criação",
            entidade="Pessoa",
            valor_anterior=None,
            valor_novo={
                "id": nova_pessoa.id,
                "nome": nova_pessoa.nome,
                "cpf_cnpj": nova_pessoa.cpf_cnpj,
            },
        )
        flash(f"Pessoa {nova_pessoa.nome} cadastrada com sucesso!", "success")
        return redirect(url_for("admin.listar_pessoas"))
    return render_template("admin/pessoas/form.html", form=form)

@admin_bp.route("/pessoas/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_pessoa(id):
    pessoa = Pessoa.query.get_or_404(id)
    form = PessoaForm(obj=pessoa)
    if form.validate_on_submit():
        pessoa_existente = Pessoa.query.filter_by(cpf_cnpj=form.cpf_cnpj.data.strip()).first()
        if pessoa_existente and pessoa_existente.id != pessoa.id:
            flash(f"Já existe outra pessoa cadastrada com o CPF/CNPJ {form.cpf_cnpj.data.strip()}.", "danger")
            return render_template("admin/pessoas/form.html", form=form, pessoa=pessoa)
        valor_anterior = {
            "id": pessoa.id,
            "nome": pessoa.nome,
            "cpf_cnpj": pessoa.cpf_cnpj,
            "email": pessoa.email,
            "telefone": pessoa.telefone,
            "endereco": pessoa.endereco,
        }
        pessoa.nome = form.nome.data.strip()
        pessoa.cpf_cnpj = form.cpf_cnpj.data.strip()
        pessoa.email = form.email.data.strip()
        pessoa.telefone = form.telefone.data.strip()
        pessoa.endereco = form.endereco.data.strip()
        db.session.commit()
        registrar_auditoria(
            acao="edição",
            entidade="Pessoa",
            valor_anterior=valor_anterior,
            valor_novo={
                "id": pessoa.id,
                "nome": pessoa.nome,
                "cpf_cnpj": pessoa.cpf_cnpj,
                "email": pessoa.email,
                "telefone": pessoa.telefone,
                "endereco": pessoa.endereco,
            },
        )
        flash(f"Pessoa {pessoa.nome} atualizada com sucesso!", "success")
        return redirect(url_for("admin.listar_pessoas"))
    return render_template("admin/pessoas/form.html", form=form, pessoa=pessoa)

@admin_bp.route("/pessoas/<int:id>/excluir", methods=["POST"])
@login_required
def excluir_pessoa(id):
    pessoa = Pessoa.query.get_or_404(id)
    if pessoa.fazendas_associadas:
        flash(
            f"Não é possível excluir a pessoa {pessoa.nome} pois ela possui fazendas associadas.",
            "danger",
        )
        return redirect(url_for("admin.listar_pessoas"))
    if pessoa.documentos and len(pessoa.documentos) > 0:
        flash(f"Não é possível excluir a pessoa {pessoa.nome} pois ela possui documentos associados.", "danger")
        return redirect(url_for("admin.listar_pessoas"))
    nome = pessoa.nome
    valor_anterior = {
        "id": pessoa.id,
        "nome": pessoa.nome,
        "cpf_cnpj": pessoa.cpf_cnpj,
        "email": pessoa.email,
        "telefone": pessoa.telefone,
        "endereco": pessoa.endereco,
    }
    db.session.delete(pessoa)
    db.session.commit()
    registrar_auditoria(
        acao="exclusão",
        entidade="Pessoa",
        valor_anterior=valor_anterior,
        valor_novo=None,
    )
    flash(f"Pessoa {nome} excluída com sucesso!", "success")
    return redirect(url_for("admin.listar_pessoas"))

@admin_bp.route("/pessoas/<int:id>/fazendas")
@login_required
def listar_fazendas_pessoa(id):
    pessoa = Pessoa.query.get_or_404(id)
    return render_template(
        "admin/pessoas/fazendas.html",
        pessoa=pessoa,
        vinculos=pessoa.pessoas_fazenda
    )

@admin_bp.route("/pessoas/<int:pessoa_id>/associar-fazenda", methods=["GET", "POST"])
@login_required
def associar_fazenda_pessoa(pessoa_id):
    pessoa = Pessoa.query.get_or_404(pessoa_id)


    # Obter fazendas que ainda não estão associadas a esta pessoa
    fazendas_associadas = [f.id for f in pessoa.fazendas_associadas]
    fazendas_disponiveis = (
        Fazenda.query.filter(~Fazenda.id.in_(fazendas_associadas)).all()
        if fazendas_associadas
        else Fazenda.query.all()
    )

    if request.method == "POST":
        fazenda_id = request.form.get("fazenda_id")
        tipo_posse = request.form.get("tipo_posse")

        if not fazenda_id:
            flash("Selecione uma fazenda.", "danger")
            return render_template(
                "admin/pessoas/associar_fazenda.html",
                pessoa=pessoa,
                fazendas=fazendas_disponiveis,
                tipos_posse=TipoPosse,
            )

        fazenda = Fazenda.query.get_or_404(fazenda_id)


        # Verificar se já está associada
        if fazenda in pessoa.fazendas_associadas:
            flash(
                f"A fazenda {fazenda.nome} já está associada a esta pessoa com esse tipo de posse.",
                "warning"
            )
            return redirect(url_for("admin.listar_fazendas_pessoa", id=pessoa.id))


        # Associar fazenda à pessoa
        pessoa.fazendas_associadas.append(fazenda)

        registrar_auditoria(
            acao="associação_fazenda",
            entidade="PessoaFazenda",
            valor_anterior=None,
            valor_novo={
                "pessoa_id": pessoa.id,
                "fazenda_id": fazenda.id,
                "tipo_posse": tipo_posse,
            },
        )
        flash(
            f"Fazenda {fazenda.nome} associada com sucesso à pessoa {pessoa.nome}!",
            "success",
        )
        return redirect(url_for("admin.listar_fazendas_pessoa", id=pessoa.id))

    return render_template(
        "admin/pessoas/associar_fazenda.html",
        pessoa=pessoa,
        fazendas=fazendas_disponiveis,
        tipos_posse=TipoPosse,
    )

@admin_bp.route(
    "/pessoas/<int:pessoa_id>/desassociar-fazenda/<int:vinculo_id>", methods=["POST"]
)
@login_required
def desassociar_fazenda_pessoa(pessoa_id, vinculo_id):
    pessoa = Pessoa.query.get_or_404(pessoa_id)
    vinculo = PessoaFazenda.query.get_or_404(vinculo_id)
    fazenda = vinculo.fazenda


    if fazenda not in pessoa.fazendas_associadas:
        flash(f"A fazenda {fazenda.nome} não está associada a esta pessoa.", "warning")
        return redirect(url_for("admin.listar_fazendas_pessoa", id=pessoa.id))

    pessoa.fazendas_associadas.remove(fazenda)

    registrar_auditoria(
        acao="desassociação_fazenda",
        entidade="PessoaFazenda",
        valor_anterior={
            "pessoa_id": pessoa.id,
            "pessoa_nome": pessoa.nome,
            "fazenda_id": fazenda.id,
            "fazenda_nome": fazenda.nome,
            "tipo_posse": vinculo.tipo_posse.value if vinculo.tipo_posse else None,
        },
        valor_novo=None,
    )

    flash(
        f"Fazenda {fazenda.nome} desassociada com sucesso da pessoa {pessoa.nome}!",
        "success",
    )
    return redirect(url_for("admin.listar_fazendas_pessoa", id=pessoa.id))


# ---------------- Fazendas ----------------

@admin_bp.route("/fazendas")
@login_required
def listar_fazendas():
    fazendas = Fazenda.query.order_by(Fazenda.nome).all()
    return render_template("admin/fazendas/listar.html", fazendas=fazendas)

@admin_bp.route("/fazendas/nova", methods=["GET", "POST"])
@login_required
def nova_fazenda():
    from src.forms.fazenda import FazendaForm, PessoaFazendaForm
    from src.models.pessoa import Pessoa

    form = FazendaForm()
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    for pf_form in form.pessoas_fazenda:
        pf_form.pessoa_id.choices = [(p.id, p.nome) for p in pessoas]

    if form.validate_on_submit():
        if form.area_consolidada.data > form.tamanho_total.data:
            flash("A área consolidada não pode ser maior que o tamanho total.", "danger")
            return render_template("admin/fazendas/form.html", form=form)

        tamanho_disponivel = form.tamanho_total.data - form.area_consolidada.data

        nova_fazenda = Fazenda(
            nome=form.nome.data.strip(),
            matricula=form.matricula.data.strip(),
            tamanho_total=form.tamanho_total.data,
            area_consolidada=form.area_consolidada.data,
            tamanho_disponivel=tamanho_disponivel,
            municipio=form.municipio.data.strip(),
            estado=form.estado.data.strip(),
            recibo_car=form.recibo_car.data.strip() if getattr(form, "recibo_car", None) and form.recibo_car.data else None,
        )

        db.session.add(nova_fazenda)
        db.session.flush()

        # Vínculos PessoaFazenda (opcional)
        for pf_form in form.pessoas_fazenda.entries:
            if pf_form.pessoa_id.data:
                vinculo = PessoaFazenda(
                    pessoa_id=pf_form.pessoa_id.data,
                    fazenda_id=nova_fazenda.id,
                    tipo_posse=pf_form.tipo_posse.data if pf_form.tipo_posse.data else None
                )
                db.session.add(vinculo)

        db.session.commit()

        registrar_auditoria(
            acao="criação",
            entidade="Fazenda",
            valor_anterior=None,
            valor_novo={
                "id": nova_fazenda.id,
                "nome": nova_fazenda.nome,
                "matricula": nova_fazenda.matricula,
            },
        )
        flash(f"Fazenda {nova_fazenda.nome} cadastrada com sucesso!", "success")
        return redirect(url_for("admin.listar_fazendas"))

    return render_template("admin/fazendas/form.html", form=form)

@admin_bp.route("/fazendas/<int:id>")
@login_required
def visualizar_fazenda(id):
    from src.models.endividamento import EndividamentoFazenda

    fazenda = Fazenda.query.get_or_404(id)
    vinculos_endividamento = EndividamentoFazenda.query.filter_by(fazenda_id=id).all()
    area_usada_credito = sum(
        float(v.hectares) for v in vinculos_endividamento
        if v.tipo == 'objeto_credito' and v.hectares
    )
    area_disponivel_credito = fazenda.tamanho_disponivel - area_usada_credito

    return render_template(
        "admin/fazendas/visualizar.html",
        fazenda=fazenda,
        vinculos_endividamento=vinculos_endividamento,
        area_usada_credito=area_usada_credito,
        area_disponivel_credito=area_disponivel_credito,
    )

@admin_bp.route("/fazendas/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_fazenda(id):
    from src.forms.fazenda import FazendaForm, PessoaFazendaForm
    from src.models.pessoa import Pessoa

    fazenda = Fazenda.query.get_or_404(id)

    if request.method == "GET":
        form = FazendaForm(obj=fazenda)
        form.pessoas_fazenda.min_entries = len(fazenda.pessoas_fazenda) or 1
        form.pessoas_fazenda.entries = []
        for vinculo in fazenda.pessoas_fazenda:
            pf_form = PessoaFazendaForm(
                pessoa_id=vinculo.pessoa_id,
                tipo_posse=vinculo.tipo_posse.name if vinculo.tipo_posse else ""
            )
            form.pessoas_fazenda.append_entry(pf_form.data)
    else:
        form = FazendaForm()

    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    for pf_form in form.pessoas_fazenda:
        pf_form.pessoa_id.choices = [(p.id, p.nome) for p in pessoas]

    if form.validate_on_submit():
        if form.area_consolidada.data > form.tamanho_total.data:
            flash("A área consolidada não pode ser maior que o tamanho total.", "danger")
            return render_template("admin/fazendas/form.html", form=form, fazenda=fazenda)

        valor_anterior = {
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

        tamanho_disponivel = form.tamanho_total.data - form.area_consolidada.data

        fazenda.nome = form.nome.data.strip()
        fazenda.matricula = form.matricula.data.strip()
        fazenda.tamanho_total = form.tamanho_total.data
        fazenda.area_consolidada = form.area_consolidada.data
        fazenda.tamanho_disponivel = tamanho_disponivel
        fazenda.municipio = form.municipio.data.strip()
        fazenda.estado = form.estado.data.strip()
        fazenda.recibo_car = form.recibo_car.data.strip() if getattr(form, "recibo_car", None) and form.recibo_car.data else None

        # Remove vínculos antigos
        for vinculo in fazenda.pessoas_fazenda:
            db.session.delete(vinculo)
        # Adiciona novos vínculos (opcional)
        for pf_form in form.pessoas_fazenda.entries:
            if pf_form.pessoa_id.data:
                vinculo = PessoaFazenda(
                    pessoa_id=pf_form.pessoa_id.data,
                    fazenda_id=fazenda.id,
                    tipo_posse=pf_form.tipo_posse.data if pf_form.tipo_posse.data else None
                )
                db.session.add(vinculo)

        db.session.commit()

        registrar_auditoria(
            acao="edição",
            entidade="Fazenda",
            valor_anterior=valor_anterior,
            valor_novo={
                "id": fazenda.id,
                "nome": fazenda.nome,
                "matricula": fazenda.matricula,
                "tamanho_total": fazenda.tamanho_total,
                "area_consolidada": fazenda.area_consolidada,
                "tamanho_disponivel": fazenda.tamanho_disponivel,
                "municipio": fazenda.municipio,
                "estado": fazenda.estado,
                "recibo_car": fazenda.recibo_car,
            },
        )
        flash(f"Fazenda {fazenda.nome} atualizada com sucesso!", "success")
        return redirect(url_for("admin.listar_fazendas"))

    return render_template("admin/fazendas/form.html", form=form, fazenda=fazenda)

@admin_bp.route("/fazendas/<int:id>/excluir", methods=["POST"])
@login_required
def excluir_fazenda(id):
    fazenda = Fazenda.query.get_or_404(id)
    if fazenda.documentos and len(fazenda.documentos) > 0:
        flash(
            f"Não é possível excluir a fazenda {fazenda.nome} pois ela possui documentos associados.",
            "danger",
        )
        return redirect(url_for("admin.listar_fazendas"))

    # Remover associações com pessoas
    for pessoa in fazenda.pessoas_associadas:
        pessoa.fazendas_associadas.remove(fazenda)


    nome = fazenda.nome
    valor_anterior = {
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
    db.session.delete(fazenda)
    db.session.commit()

    registrar_auditoria(
        acao="exclusão",
        entidade="Fazenda",
        valor_anterior=valor_anterior,
        valor_novo=None,
    )
    flash(f"Fazenda {nome} excluída com sucesso!", "success")
    return redirect(url_for("admin.listar_fazendas"))

@admin_bp.route("/fazendas/<int:id>/pessoas")
@login_required
def listar_pessoas_fazenda(id):
    """Lista todas as pessoas associadas a uma fazenda."""
    fazenda = Fazenda.query.get_or_404(id)
    return render_template(
        "admin/fazendas/pessoas.html",
        fazenda=fazenda,
        vinculos=fazenda.pessoas_fazenda
    )

@admin_bp.route("/fazendas/<int:id>/documentos")
@login_required
def listar_documentos_fazenda(id):
    fazenda = Fazenda.query.get_or_404(id)
    documentos = Documento.query.filter_by(fazenda_id=id).order_by(Documento.data_emissao.desc()).all()
    return render_template(
        "admin/fazendas/documentos.html", fazenda=fazenda, documentos=documentos
    )

# ---------------- Documentos ----------------


@admin_bp.route("/fazendas/<int:id>/pessoas")
@login_required
def listar_pessoas_fazenda(id):
    """Lista as pessoas associadas a uma fazenda específica."""
    fazenda = Fazenda.query.get_or_404(id)
    
    # Usar a nova estrutura de relacionamento
    vinculos = fazenda.pessoas_fazenda
    
    return render_template(
        "admin/fazendas/pessoas.html", 
        fazenda=fazenda, 
        vinculos=vinculos
    )


# Rotas para Documentos
@admin_bp.route("/documentos")
@login_required
def listar_documentos():
    fazendas = Fazenda.query.order_by(Fazenda.nome).all()
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()

    fazenda_id = request.args.get("fazenda_id", type=int)
    pessoa_id = request.args.get("pessoa_id", type=int)
    nome_busca = request.args.get("busca", "")

    query = Documento.query

    if fazenda_id:
        query = query.filter(Documento.fazenda_id == fazenda_id)
    if pessoa_id:
        query = query.filter(Documento.pessoa_id == pessoa_id)
    if nome_busca:
        query = query.filter(Documento.nome.ilike(f"%{nome_busca}%"))

    documentos = query.order_by(Documento.data_vencimento.asc()).all()

    return render_template(
        "admin/documentos/listar.html",
        documentos=documentos,
        fazendas=fazendas,
        pessoas=pessoas,
        fazenda_id=fazenda_id,
        pessoa_id=pessoa_id,
        nome_busca=nome_busca,
    )

@admin_bp.route("/documentos/novo", methods=["GET", "POST"])
@login_required
def novo_documento():
    fazendas = Fazenda.query.order_by(Fazenda.nome).all()
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    tipos_documento = TipoDocumento

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        tipo = request.form.get("tipo", "").strip()
        tipo_personalizado = request.form.get("tipo_personalizado", "").strip()
        data_emissao = request.form.get("data_emissao", "").strip()
        data_vencimento = request.form.get("data_vencimento", "").strip()
        emails_notificacao = request.form.get("emails_notificacao", "").strip()
        fazenda_id = request.form.get("fazenda_id") or None
        pessoa_id = request.form.get("pessoa_id") or None

        prazos_notificacao = request.form.getlist("prazo_notificacao[]")
        prazos_notificacao = [int(p) for p in prazos_notificacao if p.isdigit()]

        if not nome or not tipo or not data_emissao:
            flash("Todos os campos com * são obrigatórios.", "danger")
            return render_template(
                "admin/documentos/form.html",
                tipos_documento=tipos_documento,
                fazendas=fazendas,
                pessoas=pessoas,
            )
        if not fazenda_id and not pessoa_id:
            flash("Selecione uma fazenda/área e/ou uma pessoa para relacionar o documento.", "danger")
            return render_template(
                "admin/documentos/form.html",
                tipos_documento=tipos_documento,
                fazendas=fazendas,
                pessoas=pessoas,
            )
        if tipo == "Outros" and not tipo_personalizado:
            flash(
                'Para o tipo "Outros", é necessário informar o tipo personalizado.',
                "danger",
            )
            return render_template(
                "admin/documentos/form.html",
                tipos_documento=tipos_documento,
                fazendas=fazendas,
                pessoas=pessoas,
            )
        try:
            data_emissao = datetime.datetime.strptime(data_emissao, "%Y-%m-%d").date()
            data_vencimento = (
                datetime.datetime.strptime(data_vencimento, "%Y-%m-%d").date()
                if data_vencimento
                else None
            )
        except Exception:
            flash("Formato de data inválido.", "danger")
            return render_template(
                "admin/documentos/form.html",
                tipos_documento=tipos_documento,
                fazendas=fazendas,
                pessoas=pessoas,
            )

        novo_documento = Documento(
            nome=nome,
            tipo=TipoDocumento(tipo),
            tipo_personalizado=tipo_personalizado if tipo == "Outros" else None,
            data_emissao=data_emissao,
            data_vencimento=data_vencimento,
            fazenda_id=int(fazenda_id) if fazenda_id else None,
            pessoa_id=int(pessoa_id) if pessoa_id else None,
        )
        novo_documento.emails_notificacao = emails_notificacao
        novo_documento.prazos_notificacao = prazos_notificacao
        db.session.add(novo_documento)
        db.session.commit()
        registrar_auditoria(
            acao="criação",
            entidade="Documento",
            valor_anterior=None,
            valor_novo={
                "id": novo_documento.id,
                "nome": novo_documento.nome,
                "tipo": novo_documento.tipo.value,
                "tipo_personalizado": novo_documento.tipo_personalizado,
                "data_emissao": str(novo_documento.data_emissao),
                "data_vencimento": (
                    str(novo_documento.data_vencimento)
                    if novo_documento.data_vencimento
                    else None
                ),
                "fazenda_id": novo_documento.fazenda_id,
                "pessoa_id": novo_documento.pessoa_id,
                "emails_notificacao": novo_documento.emails_notificacao,
                "prazos_notificacao": novo_documento.prazos_notificacao,
            },
        )
        flash(f"Documento {nome} cadastrado com sucesso!", "success")
        return redirect(url_for("admin.listar_documentos"))

    return render_template(
        "admin/documentos/form.html",
        tipos_documento=tipos_documento,
        fazendas=fazendas,
        pessoas=pessoas,
    )

@admin_bp.route("/documentos/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_documento(id):
    documento = Documento.query.get_or_404(id)
    fazendas = Fazenda.query.order_by(Fazenda.nome).all()
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    tipos_documento = TipoDocumento

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        tipo = request.form.get("tipo", "").strip()
        tipo_personalizado = request.form.get("tipo_personalizado", "").strip()
        data_emissao = request.form.get("data_emissao", "").strip()
        data_vencimento = request.form.get("data_vencimento", "").strip()
        emails_notificacao = request.form.get("emails_notificacao", "").strip()
        fazenda_id = request.form.get("fazenda_id") or None
        pessoa_id = request.form.get("pessoa_id") or None

        prazos_notificacao = request.form.getlist("prazo_notificacao[]")
        prazos_notificacao = [int(p) for p in prazos_notificacao if str(p).isdigit()]

        if not nome or not tipo or not data_emissao:
            flash("Todos os campos com * são obrigatórios.", "danger")
            return render_template(
                "admin/documentos/form.html",
                documento=documento,
                tipos_documento=tipos_documento,
                fazendas=fazendas,
                pessoas=pessoas,
            )
        if not fazenda_id and not pessoa_id:
            flash("Selecione uma fazenda/área e/ou uma pessoa para relacionar o documento.", "danger")
            return render_template(
                "admin/documentos/form.html",
                documento=documento,
                tipos_documento=tipos_documento,
                fazendas=fazendas,
                pessoas=pessoas,
            )
        if tipo == "Outros" and not tipo_personalizado:
            flash(
                'Para o tipo "Outros", é necessário informar o tipo personalizado.',
                "danger",
            )
            return render_template(
                "admin/documentos/form.html",
                documento=documento,
                tipos_documento=tipos_documento,
                fazendas=fazendas,
                pessoas=pessoas,
            )
        try:
            data_emissao = datetime.datetime.strptime(data_emissao, "%Y-%m-%d").date()
            data_vencimento = (
                datetime.datetime.strptime(data_vencimento, "%Y-%m-%d").date()
                if data_vencimento
                else None
            )
        except Exception:
            flash("Formato de data inválido.", "danger")
            return render_template(
                "admin/documentos/form.html",
                documento=documento,
                tipos_documento=tipos_documento,
                fazendas=fazendas,
                pessoas=pessoas,
            )

        valor_anterior = {
            "id": documento.id,
            "nome": documento.nome,
            "tipo": documento.tipo.value if documento.tipo else None,
            "tipo_personalizado": documento.tipo_personalizado,
            "data_emissao": str(documento.data_emissao),
            "data_vencimento": (
                str(documento.data_vencimento) if documento.data_vencimento else None
            ),
            "fazenda_id": documento.fazenda_id,
            "pessoa_id": documento.pessoa_id,
            "emails_notificacao": documento.emails_notificacao,
            "prazos_notificacao": documento.prazos_notificacao,
        }

        documento.nome = nome
        documento.tipo = TipoDocumento(tipo)
        documento.tipo_personalizado = tipo_personalizado if tipo == "Outros" else None
        documento.data_emissao = data_emissao
        documento.data_vencimento = data_vencimento
        documento.fazenda_id = int(fazenda_id) if fazenda_id else None
        documento.pessoa_id = int(pessoa_id) if pessoa_id else None
        documento.emails_notificacao = emails_notificacao
        documento.prazos_notificacao = prazos_notificacao

        db.session.commit()

        registrar_auditoria(
            acao="edição",
            entidade="Documento",
            valor_anterior=valor_anterior,
            valor_novo={
                "id": documento.id,
                "nome": documento.nome,
                "tipo": documento.tipo.value if documento.tipo else None,
                "tipo_personalizado": documento.tipo_personalizado,
                "data_emissao": str(documento.data_emissao),
                "data_vencimento": (
                    str(documento.data_vencimento)
                    if documento.data_vencimento
                    else None
                ),
                "fazenda_id": documento.fazenda_id,
                "pessoa_id": documento.pessoa_id,
                "emails_notificacao": documento.emails_notificacao,
                "prazos_notificacao": documento.prazos_notificacao,
            },
        )
        flash(f"Documento {nome} atualizado com sucesso!", "success")
        return redirect(url_for("admin.listar_documentos"))

    return render_template(
        "admin/documentos/form.html",
        documento=documento,
        tipos_documento=tipos_documento,
        fazendas=fazendas,
        pessoas=pessoas,
    )

@admin_bp.route("/documentos/<int:id>/excluir", methods=["POST"])
@login_required
def excluir_documento(id):
    documento = Documento.query.get_or_404(id)
    nome = documento.nome
    valor_anterior = {
        "id": documento.id,
        "nome": documento.nome,
        "tipo": documento.tipo.value if documento.tipo else None,
        "tipo_personalizado": documento.tipo_personalizado,
        "data_emissao": str(documento.data_emissao),
        "data_vencimento": (
            str(documento.data_vencimento) if documento.data_vencimento else None
        ),
        "fazenda_id": documento.fazenda_id,
        "pessoa_id": documento.pessoa_id,
        "emails_notificacao": documento.emails_notificacao,
        "prazos_notificacao": documento.prazos_notificacao,
    }
    db.session.delete(documento)
    db.session.commit()
    registrar_auditoria(
        acao="exclusão",
        entidade="Documento",
        valor_anterior=valor_anterior,
        valor_novo=None,
    )
    flash(f"Documento {nome} excluído com sucesso!", "success")
    return redirect(url_for("admin.listar_documentos"))

@admin_bp.route("/documentos/vencidos")
@login_required
def listar_documentos_vencidos():
    hoje = datetime.date.today()

    documentos_vencidos = (
        Documento.query.filter(Documento.data_vencimento < hoje)
        .order_by(Documento.data_vencimento)
        .all()
    )

    data_limite = hoje + datetime.timedelta(days=30)
    documentos_proximos = (
        Documento.query.filter(
            Documento.data_vencimento >= hoje,
            Documento.data_vencimento <= data_limite
        ).order_by(Documento.data_vencimento).all()
    )

    for doc in documentos_proximos:
        prazos = doc.prazos_notificacao if doc.prazos_notificacao else [30, 15, 7, 1]
        prazos = [int(p) for p in prazos]
        enviados = []
        doc.proximas_notificacoes = calcular_proximas_notificacoes_programadas(
            doc.data_vencimento, prazos, enviados
        )

    return render_template(
        "admin/documentos/vencidos.html",
        documentos_vencidos=documentos_vencidos,
        documentos_proximos=documentos_proximos,
    )

@admin_bp.route("/documentos/notificacoes", methods=["GET", "POST"])
@login_required
def notificacoes_documentos():
    documentos_por_prazo = verificar_documentos_vencendo()
    if request.method == "POST":
        total = 0
        enviados = 0
        erros = []
        for prazo, docs in documentos_por_prazo.items():
            for doc in docs:
                emails = []
                if hasattr(doc, "emails_notificacao") and doc.emails_notificacao:
                    if isinstance(doc.emails_notificacao, list):
                        emails = doc.emails_notificacao
                    else:
                        emails = [
                            e.strip()
                            for e in doc.emails_notificacao.split(",")
                            if e.strip()
                        ]
                if not emails:
                    continue
                assunto, corpo_html = formatar_email_notificacao(doc, prazo)
                enviado = EmailService().send_email(
                    emails, assunto, corpo_html, html=True
                )
                total += 1
                if enviado:
                    enviados += 1
                else:
                    erros.append(doc.nome)
        if enviados:
            flash(
                f"{enviados} de {total} notificações enviadas com sucesso!", "success"
            )
        else:
            flash(
                "Nenhuma notificação enviada. Verifique se há e-mails cadastrados.",
                "warning",
            )
        if erros:
            flash(f'Falha ao enviar notificação para: {", ".join(erros)}', "danger")
        return redirect(url_for("admin.notificacoes_documentos"))
    return render_template(
        "admin/documentos/notificacoes.html", documentos_por_prazo=documentos_por_prazo
    )

@admin_bp.route("/testar-email", methods=["POST"])
@login_required
def testar_email():
    emails = request.form.get("emails", "")
    if not emails:
        return jsonify({"sucesso": False, "mensagem": "Nenhum e-mail informado."})
    lista_emails = [email.strip() for email in emails.split(",") if email.strip()]
    if not lista_emails:
        return jsonify({"sucesso": False, "mensagem": "Formato de e-mail inválido."})
    sucesso = EmailService().enviar_email_teste(lista_emails)
    mensagem = (
        "E-mail de teste enviado com sucesso."
        if sucesso
        else "Falha ao enviar e-mail de teste. Verifique as configurações."
    )
    return jsonify({"sucesso": sucesso, "mensagem": mensagem})