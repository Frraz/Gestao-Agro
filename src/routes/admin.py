# /src/routes/admin.py

from datetime import date, datetime, timedelta

from flask import (
    Blueprint, flash, jsonify, redirect, render_template,
    request, url_for, current_app
)
from flask_login import login_required

from src.utils.database import paginate_query, safe_count
from src.utils.notificacao_utils import calcular_proximas_notificacoes_programadas
from src.models.db import db
from src.models.documento import Documento, TipoDocumento
from src.models.endividamento import Endividamento  # Adicionado para dashboard
from src.models.fazenda import Fazenda, TipoPosse
from src.models.pessoa import Pessoa
from src.utils.auditoria import registrar_auditoria
from src.utils.email_service import (
    EmailService, formatar_email_notificacao, verificar_documentos_vencendo
)
from sqlalchemy import func

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
def index():
    """Página inicial do painel administrativo."""
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    try:
        hoje = date.today()
        dias_proximos_doc = 30
        dias_proximos_end = 30

        # Obter parâmetros de paginação
        prox_page = int(request.args.get("prox_page", 1))
        venc_page = int(request.args.get("venc_page", 1))
        per_page = 10

        # Documentos próximos (até 30 dias)
        docs_proximos_query = Documento.query.filter(
            Documento.data_vencimento >= hoje,
            Documento.data_vencimento <= hoje + timedelta(days=dias_proximos_doc)
        ).order_by(Documento.data_vencimento.asc())
        docs_proximos, total_proximos, total_pag_proximos = paginate_query(
            docs_proximos_query, prox_page, per_page
        )

        # Documentos vencidos
        docs_vencidos_query = Documento.query.filter(
            Documento.data_vencimento < hoje
        ).order_by(Documento.data_vencimento.asc())
        docs_vencidos, total_vencidos, total_pag_vencidos = paginate_query(
            docs_vencidos_query, venc_page, per_page
        )

        # Documentos em dia
        total_documentos = safe_count(Documento)
        docs_em_dia = max(0, total_documentos - len(docs_proximos) - len(docs_vencidos))

        # Endividamentos próximos (até 30 dias)
        end_proximos_query = Endividamento.query.filter(
            Endividamento.data_vencimento_final >= hoje,
            Endividamento.data_vencimento_final <= hoje + timedelta(days=dias_proximos_end)
        ).order_by(Endividamento.data_vencimento_final.asc())
        endividamentos_proximos = end_proximos_query.all()

        # Endividamentos vencidos
        end_vencidos_query = Endividamento.query.filter(
            Endividamento.data_vencimento_final < hoje
        ).order_by(Endividamento.data_vencimento_final.asc())
        endividamentos_vencidos = end_vencidos_query.all()

        # Endividamentos em dia
        total_endividamentos = safe_count(Endividamento)
        end_em_dia = max(0, total_endividamentos - len(endividamentos_proximos) - len(endividamentos_vencidos))

        # Contadores gerais
        total_pessoas = safe_count(Pessoa)
        total_fazendas = safe_count(Fazenda)

        # Notificações pendentes (implemente conforme sua lógica)
        notificacoes_pendentes = []  # Substitua pela busca real

        return render_template(
            "admin/index.html",
            total_pessoas=total_pessoas,
            total_fazendas=total_fazendas,
            total_documentos=total_documentos,
            documentos_proximos=docs_proximos,
            documentos_vencidos=docs_vencidos,
            docs_em_dia=docs_em_dia,
            prox_page=prox_page,
            total_pag_proximos=total_pag_proximos,
            venc_page=venc_page,
            total_pag_vencidos=total_pag_vencidos,
            total_endividamentos=total_endividamentos,
            endividamentos_proximos=endividamentos_proximos,
            endividamentos_vencidos=endividamentos_vencidos,
            end_em_dia=end_em_dia,
            notificacoes_pendentes=notificacoes_pendentes,
            now=datetime.now()
        )

    except Exception as e:
        current_app.logger.error(f"Erro no dashboard: {e}", exc_info=True)
        flash("Ocorreu um erro ao carregar o dashboard. Por favor, tente novamente.", "danger")
        return render_template(
            "admin/dashboard_error.html",
            error=str(e),
            now=datetime.now()
        )

# --- Rotas para Pessoas ---
@admin_bp.route("/pessoas")
@login_required
def listar_pessoas():
    pessoas = Pessoa.query.all()
    return render_template("admin/pessoas/listar.html", pessoas=pessoas)


@admin_bp.route("/pessoas/nova", methods=["GET", "POST"])
@login_required
def nova_pessoa():
    if request.method == "POST":
        nome = request.form.get("nome")
        cpf_cnpj = request.form.get("cpf_cnpj")
        email = request.form.get("email")
        telefone = request.form.get("telefone")
        endereco = request.form.get("endereco")
        if not nome or not cpf_cnpj:
            flash("Nome e CPF/CNPJ são obrigatórios.", "danger")
            return render_template("admin/pessoas/form.html")
        pessoa_existente = Pessoa.query.filter_by(cpf_cnpj=cpf_cnpj).first()
        if pessoa_existente:
            flash(
                f"Já existe uma pessoa cadastrada com o CPF/CNPJ {cpf_cnpj}.", "danger"
            )
            return render_template("admin/pessoas/form.html")
        nova_pessoa = Pessoa(
            nome=nome,
            cpf_cnpj=cpf_cnpj,
            email=email,
            telefone=telefone,
            endereco=endereco,
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
        flash(f"Pessoa {nome} cadastrada com sucesso!", "success")
        return redirect(url_for("admin.listar_pessoas"))
    return render_template("admin/pessoas/form.html")


@admin_bp.route("/pessoas/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_pessoa(id):
    pessoa = Pessoa.query.get_or_404(id)
    if request.method == "POST":
        nome = request.form.get("nome")
        cpf_cnpj = request.form.get("cpf_cnpj")
        email = request.form.get("email")
        telefone = request.form.get("telefone")
        endereco = request.form.get("endereco")
        if not nome or not cpf_cnpj:
            flash("Nome e CPF/CNPJ são obrigatórios.", "danger")
            return render_template("admin/pessoas/form.html", pessoa=pessoa)
        pessoa_existente = Pessoa.query.filter_by(cpf_cnpj=cpf_cnpj).first()
        if pessoa_existente and pessoa_existente.id != pessoa.id:
            flash(
                f"Já existe outra pessoa cadastrada com o CPF/CNPJ {cpf_cnpj}.",
                "danger",
            )
            return render_template("admin/pessoas/form.html", pessoa=pessoa)
        valor_anterior = {
            "id": pessoa.id,
            "nome": pessoa.nome,
            "cpf_cnpj": pessoa.cpf_cnpj,
            "email": pessoa.email,
            "telefone": pessoa.telefone,
            "endereco": pessoa.endereco,
        }
        pessoa.nome = nome
        pessoa.cpf_cnpj = cpf_cnpj
        pessoa.email = email
        pessoa.telefone = telefone
        pessoa.endereco = endereco
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
        flash(f"Pessoa {nome} atualizada com sucesso!", "success")
        return redirect(url_for("admin.listar_pessoas"))
    return render_template("admin/pessoas/form.html", pessoa=pessoa)


@admin_bp.route("/pessoas/<int:id>/excluir", methods=["POST"])
@login_required
def excluir_pessoa(id):
    pessoa = Pessoa.query.get_or_404(id)
    if pessoa.fazendas:
        flash(
            f"Não é possível excluir a pessoa {pessoa.nome} pois ela possui fazendas associadas.",
            "danger",
        )
        return redirect(url_for("admin.listar_pessoas"))
    if hasattr(pessoa, "documentos") and pessoa.documentos:
        flash(
            f"Não é possível excluir a pessoa {pessoa.nome} pois ela possui documentos associados.",
            "danger",
        )
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
    """Lista as fazendas associadas a uma pessoa."""
    pessoa = Pessoa.query.get_or_404(id)
    return render_template("admin/pessoas/fazendas.html", pessoa=pessoa)


@admin_bp.route("/pessoas/<int:pessoa_id>/associar-fazenda", methods=["GET", "POST"])
@login_required
def associar_fazenda_pessoa(pessoa_id):
    """Associa uma fazenda a uma pessoa."""
    pessoa = Pessoa.query.get_or_404(pessoa_id)
    fazendas_associadas = [f.id for f in pessoa.fazendas]
    fazendas_disponiveis = (
        Fazenda.query.filter(~Fazenda.id.in_(fazendas_associadas)).all()
        if fazendas_associadas
        else Fazenda.query.all()
    )

    if request.method == "POST":
        fazenda_id = request.form.get("fazenda_id")
        if not fazenda_id:
            flash("Selecione uma fazenda para associar.", "danger")
            return render_template(
                "admin/pessoas/associar_fazenda.html",
                pessoa=pessoa,
                fazendas=fazendas_disponiveis,
            )
        fazenda = Fazenda.query.get_or_404(fazenda_id)
        if fazenda in pessoa.fazendas:
            flash(
                f"A fazenda {fazenda.nome} já está associada a esta pessoa.", "warning"
            )
            return redirect(url_for("admin.listar_fazendas_pessoa", id=pessoa.id))
        pessoa.fazendas.append(fazenda)
        registrar_auditoria(
            acao="associação_fazenda",
            entidade="Pessoa-Fazenda",
            valor_anterior=None,
            valor_novo={
                "pessoa_id": pessoa.id,
                "pessoa_nome": pessoa.nome,
                "fazenda_id": fazenda.id,
                "fazenda_nome": fazenda.nome,
            },
        )
        db.session.commit()
        flash(
            f"Fazenda {fazenda.nome} associada com sucesso à pessoa {pessoa.nome}!",
            "success",
        )
        return redirect(url_for("admin.listar_fazendas_pessoa", id=pessoa.id))

    return render_template(
        "admin/pessoas/associar_fazenda.html",
        pessoa=pessoa,
        fazendas=fazendas_disponiveis,
    )


@admin_bp.route(
    "/pessoas/<int:pessoa_id>/desassociar-fazenda/<int:fazenda_id>", methods=["POST"]
)
@login_required
def desassociar_fazenda_pessoa(pessoa_id, fazenda_id):
    """Desassocia uma fazenda de uma pessoa."""
    pessoa = Pessoa.query.get_or_404(pessoa_id)
    fazenda = Fazenda.query.get_or_404(fazenda_id)
    if fazenda not in pessoa.fazendas:
        flash(f"A fazenda {fazenda.nome} não está associada a esta pessoa.", "warning")
        return redirect(url_for("admin.listar_fazendas_pessoa", id=pessoa.id))
    pessoa.fazendas.remove(fazenda)
    registrar_auditoria(
        acao="desassociação_fazenda",
        entidade="Pessoa-Fazenda",
        valor_anterior={
            "pessoa_id": pessoa.id,
            "pessoa_nome": pessoa.nome,
            "fazenda_id": fazenda.id,
            "fazenda_nome": fazenda.nome,
        },
        valor_novo=None,
    )
    db.session.commit()
    flash(
        f"Fazenda {fazenda.nome} desassociada com sucesso da pessoa {pessoa.nome}!",
        "success",
    )
    return redirect(url_for("admin.listar_fazendas_pessoa", id=pessoa.id))


# Rotas para Fazendas
@admin_bp.route("/fazendas")
@login_required
def listar_fazendas():
    """Lista todas as fazendas cadastradas."""
    fazendas = Fazenda.query.all()
    return render_template("admin/fazendas/listar.html", fazendas=fazendas)


@admin_bp.route("/fazendas/nova", methods=["GET", "POST"])
@login_required
def nova_fazenda():
    """Cadastra uma nova fazenda."""
    if request.method == "POST":
        nome = request.form.get("nome")
        matricula = request.form.get("matricula")
        tamanho_total = request.form.get("tamanho_total")
        area_consolidada = request.form.get("area_consolidada")
        tipo_posse = request.form.get("tipo_posse")
        municipio = request.form.get("municipio")
        estado = request.form.get("estado")
        recibo_car = request.form.get("recibo_car")

        # Validação básica
        if (
            not nome
            or not matricula
            or not tamanho_total
            or not area_consolidada
            or not tipo_posse
            or not municipio
            or not estado
        ):
            flash("Todos os campos com * são obrigatórios.", "danger")
            return render_template("admin/fazendas/form.html", tipos_posse=TipoPosse)

        # Verificar se já existe fazenda com a mesma matrícula
        fazenda_existente = Fazenda.query.filter_by(matricula=matricula).first()
        if fazenda_existente:
            flash(
                f"Já existe uma fazenda cadastrada com a matrícula {matricula}.",
                "danger",
            )
            return render_template("admin/fazendas/form.html", tipos_posse=TipoPosse)

        # Converter valores para float
        try:
            tamanho_total = float(tamanho_total)
            area_consolidada = float(area_consolidada)
        except ValueError:
            flash("Os valores de tamanho devem ser numéricos.", "danger")
            return render_template("admin/fazendas/form.html", tipos_posse=TipoPosse)

        # Validar tamanhos
        if area_consolidada > tamanho_total:
            flash(
                "A área consolidada não pode ser maior que o tamanho total.", "danger"
            )
            return render_template("admin/fazendas/form.html", tipos_posse=TipoPosse)

        # Calcular tamanho disponível
        tamanho_disponivel = tamanho_total - area_consolidada

        # Criar nova fazenda
        nova_fazenda = Fazenda(
            nome=nome,
            matricula=matricula,
            tamanho_total=tamanho_total,
            area_consolidada=area_consolidada,
            tamanho_disponivel=tamanho_disponivel,
            tipo_posse=TipoPosse(tipo_posse),
            municipio=municipio,
            estado=estado,
            recibo_car=recibo_car,
        )

        db.session.add(nova_fazenda)
        db.session.commit()

        # LOG DE AUDITORIA
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
        flash(f"Fazenda {nome} cadastrada com sucesso!", "success")
        return redirect(url_for("admin.listar_fazendas"))
    return render_template("admin/fazendas/form.html", tipos_posse=TipoPosse)


@admin_bp.route("/fazendas/<int:id>")
@login_required
def visualizar_fazenda(id):
    """Visualiza detalhes de uma fazenda."""
    from src.models.endividamento import EndividamentoFazenda

    fazenda = Fazenda.query.get_or_404(id)

    # Obter vínculos com endividamentos
    vinculos_endividamento = EndividamentoFazenda.query.filter_by(fazenda_id=id).all()

    # Calcular área utilizada em créditos
    area_usada_credito = sum(
        float(v.hectares) for v in vinculos_endividamento
        if v.tipo == 'objeto_credito' and v.hectares
    )

    # Calcular área disponível para crédito
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
    """Edita uma fazenda existente."""
    fazenda = Fazenda.query.get_or_404(id)

    if request.method == "POST":
        nome = request.form.get("nome")
        matricula = request.form.get("matricula")
        tamanho_total = request.form.get("tamanho_total")
        area_consolidada = request.form.get("area_consolidada")
        tipo_posse = request.form.get("tipo_posse")
        municipio = request.form.get("municipio")
        estado = request.form.get("estado")
        recibo_car = request.form.get("recibo_car")

        # Validação básica
        if (
            not nome
            or not matricula
            or not tamanho_total
            or not area_consolidada
            or not tipo_posse
            or not municipio
            or not estado
        ):
            flash("Todos os campos com * são obrigatórios.", "danger")
            return render_template(
                "admin/fazendas/form.html", fazenda=fazenda, tipos_posse=TipoPosse
            )

        # Verificar se já existe outra fazenda com a mesma matrícula
        fazenda_existente = Fazenda.query.filter_by(matricula=matricula).first()
        if fazenda_existente and fazenda_existente.id != fazenda.id:
            flash(
                f"Já existe outra fazenda cadastrada com a matrícula {matricula}.",
                "danger",
            )
            return render_template(
                "admin/fazendas/form.html", fazenda=fazenda, tipos_posse=TipoPosse
            )

        # Converter valores para float
        try:
            tamanho_total = float(tamanho_total)
            area_consolidada = float(area_consolidada)
        except ValueError:
            flash("Os valores de tamanho devem ser numéricos.", "danger")
            return render_template(
                "admin/fazendas/form.html", fazenda=fazenda, tipos_posse=TipoPosse
            )

        # Validar tamanhos
        if area_consolidada > tamanho_total:
            flash(
                "A área consolidada não pode ser maior que o tamanho total.", "danger"
            )
            return render_template(
                "admin/fazendas/form.html", fazenda=fazenda, tipos_posse=TipoPosse
            )

        # Captura os dados antigos antes de modificar
        valor_anterior = {
            "id": fazenda.id,
            "nome": fazenda.nome,
            "matricula": fazenda.matricula,
            "tamanho_total": fazenda.tamanho_total,
            "area_consolidada": fazenda.area_consolidada,
            "tamanho_disponivel": fazenda.tamanho_disponivel,
            "tipo_posse": fazenda.tipo_posse.value if fazenda.tipo_posse else None,
            "municipio": fazenda.municipio,
            "estado": fazenda.estado,
            "recibo_car": fazenda.recibo_car,
        }

        # Calcular tamanho disponível
        tamanho_disponivel = tamanho_total - area_consolidada

        # Atualizar fazenda
        fazenda.nome = nome
        fazenda.matricula = matricula
        fazenda.tamanho_total = tamanho_total
        fazenda.area_consolidada = area_consolidada
        fazenda.tamanho_disponivel = tamanho_disponivel
        fazenda.tipo_posse = TipoPosse(tipo_posse)
        fazenda.municipio = municipio
        fazenda.estado = estado
        fazenda.recibo_car = recibo_car

        db.session.commit()

        # LOG DE AUDITORIA
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
                "tipo_posse": fazenda.tipo_posse.value if fazenda.tipo_posse else None,
                "municipio": fazenda.municipio,
                "estado": fazenda.estado,
                "recibo_car": fazenda.recibo_car,
            },
        )
        flash(f"Fazenda {nome} atualizada com sucesso!", "success")
        return redirect(url_for("admin.listar_fazendas"))
    return render_template(
        "admin/fazendas/form.html", fazenda=fazenda, tipos_posse=TipoPosse
    )


@admin_bp.route("/fazendas/<int:id>/excluir", methods=["POST"])
@login_required
def excluir_fazenda(id):
    """Exclui uma fazenda do sistema."""
    fazenda = Fazenda.query.get_or_404(id)

    # Verificar se a fazenda tem documentos associados
    if fazenda.documentos:
        flash(
            f"Não é possível excluir a fazenda {fazenda.nome} pois ela possui documentos associados.",
            "danger",
        )
        return redirect(url_for("admin.listar_fazendas"))

    # Remover associações com pessoas
    for pessoa in fazenda.pessoas:
        pessoa.fazendas.remove(fazenda)

    nome = fazenda.nome
    # Capture o estado anterior antes do delete
    valor_anterior = {
        "id": fazenda.id,
        "nome": fazenda.nome,
        "matricula": fazenda.matricula,
        "tamanho_total": fazenda.tamanho_total,
        "area_consolidada": fazenda.area_consolidada,
        "tamanho_disponivel": fazenda.tamanho_disponivel,
        "tipo_posse": fazenda.tipo_posse.value if fazenda.tipo_posse else None,
        "municipio": fazenda.municipio,
        "estado": fazenda.estado,
        "recibo_car": fazenda.recibo_car,
    }
    db.session.delete(fazenda)
    db.session.commit()

    # LOG DE AUDITORIA
    registrar_auditoria(
        acao="exclusão",
        entidade="Fazenda",
        valor_anterior=valor_anterior,
        valor_novo=None,
    )
    flash(f"Fazenda {nome} excluída com sucesso!", "success")
    return redirect(url_for("admin.listar_fazendas"))


@admin_bp.route("/fazendas/<int:id>/documentos")
@login_required
def listar_documentos_fazenda(id):
    """Lista os documentos associados a uma fazenda."""
    fazenda = Fazenda.query.get_or_404(id)
    documentos = Documento.query.filter_by(fazenda_id=id).all()
    return render_template(
        "admin/fazendas/documentos.html", fazenda=fazenda, documentos=documentos
    )


# Rotas para Documentos
@admin_bp.route("/documentos")
@login_required
def listar_documentos():
    """Lista todos os documentos cadastrados, com filtros."""
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
    """Cadastra um novo documento."""
    fazendas = Fazenda.query.all()
    pessoas = Pessoa.query.all()
    tipos_documento = TipoDocumento  # Enum para template

    if request.method == "POST":
        nome = request.form.get("nome")
        tipo = request.form.get("tipo")
        tipo_personalizado = request.form.get("tipo_personalizado")
        data_emissao = request.form.get("data_emissao")
        data_vencimento = request.form.get("data_vencimento")
        emails_notificacao = request.form.get("emails_notificacao")
        fazenda_id = request.form.get("fazenda_id") or None
        pessoa_id = request.form.get("pessoa_id") or None

        prazos_notificacao = request.form.getlist("prazo_notificacao[]")
        prazos_notificacao = [int(p) for p in prazos_notificacao if p.isdigit()]

        # Validação básica
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
        # Converter datas
        try:
            data_emissao = datetime.strptime(data_emissao, "%Y-%m-%d").date()
            data_vencimento = (
                datetime.strptime(data_vencimento, "%Y-%m-%d").date()
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

        # Criar documento
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
    """Edita um documento existente."""
    documento = Documento.query.get_or_404(id)
    fazendas = Fazenda.query.all()
    pessoas = Pessoa.query.all()

    if request.method == "POST":
        nome = request.form.get("nome")
        tipo = request.form.get("tipo")
        tipo_personalizado = request.form.get("tipo_personalizado")
        data_emissao = request.form.get("data_emissao")
        data_vencimento = request.form.get("data_vencimento")
        emails_notificacao = request.form.get("emails_notificacao")
        fazenda_id = request.form.get("fazenda_id") or None
        pessoa_id = request.form.get("pessoa_id") or None

        # Obter múltiplos prazos de notificação
        prazos_notificacao = request.form.getlist("prazo_notificacao[]")
        if not prazos_notificacao:
            prazos_notificacao = []
        else:
            prazos_notificacao = [int(prazo) for prazo in prazos_notificacao if str(prazo).isdigit()]

        # Validação básica
        if not nome or not tipo or not data_emissao:
            flash("Todos os campos com * são obrigatórios.", "danger")
            return render_template(
                "admin/documentos/form.html",
                documento=documento,
                tipos_documento=TipoDocumento,
                fazendas=fazendas,
                pessoas=pessoas,
            )

        if not fazenda_id and not pessoa_id:
            flash("Selecione uma fazenda/área e/ou uma pessoa para relacionar o documento.", "danger")
            return render_template(
                "admin/documentos/form.html",
                documento=documento,
                tipos_documento=TipoDocumento,
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
                tipos_documento=TipoDocumento,
                fazendas=fazendas,
                pessoas=pessoas,
            )

        # Converter datas
        try:
            data_emissao = datetime.strptime(data_emissao, "%Y-%m-%d").date()
            if data_vencimento:
                data_vencimento = datetime.strptime(
                    data_vencimento, "%Y-%m-%d"
                ).date()
            else:
                data_vencimento = None
        except ValueError:
            flash("Formato de data inválido.", "danger")
            return render_template(
                "admin/documentos/form.html",
                documento=documento,
                tipos_documento=TipoDocumento,
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
        tipos_documento=TipoDocumento,
        fazendas=fazendas,
        pessoas=pessoas,
    )


@admin_bp.route("/documentos/<int:id>/excluir", methods=["POST"])
@login_required
def excluir_documento(id):
    """Exclui um documento do sistema."""
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
    """Lista documentos vencidos ou próximos do vencimento."""
    hoje = date.today()

    documentos_vencidos = (
        Documento.query.filter(Documento.data_vencimento < hoje)
        .order_by(Documento.data_vencimento)
        .all()
    )

    data_limite = hoje + timedelta(days=30)
    documentos_proximos = (
        Documento.query.filter(
            Documento.data_vencimento >= hoje,
            Documento.data_vencimento <= data_limite
        ).order_by(Documento.data_vencimento).all()
    )

    # Garante que os prazos estão como inteiros para cálculo correto das notificações programadas
    for doc in documentos_proximos:
        prazos = doc.prazos_notificacao if doc.prazos_notificacao else [30, 15, 7, 1]
        prazos = [int(p) for p in prazos]
        enviados = []  # Se houver histórico, preencha
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
    """Gerencia notificações de vencimento de documentos."""
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