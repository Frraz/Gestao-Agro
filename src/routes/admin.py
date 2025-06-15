from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from src.models.db import db
from src.models.documento import Documento, TipoDocumento, TipoEntidade
from src.models.fazenda import Fazenda, TipoPosse
from src.models.pessoa import Pessoa
import os
import datetime
from src.utils.email_service import verificar_documentos_vencendo, EmailService
from flask_login import login_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
def index():
    """Página inicial do painel administrativo."""
    # Contadores
    total_pessoas = Pessoa.query.count()
    total_fazendas = Fazenda.query.count()
    total_documentos = Documento.query.count()
    
    # Documentos vencidos ou próximos do vencimento
    documentos = Documento.query.filter(Documento.data_vencimento.isnot(None)).all()
    documentos_vencidos = []
    documentos_proximos = []
    
    for documento in documentos:
        if documento.esta_vencido:
            documentos_vencidos.append(documento)
        elif documento.precisa_notificar:
            documentos_proximos.append(documento)
    
    return render_template('admin/index.html', 
                          total_pessoas=total_pessoas,
                          total_fazendas=total_fazendas,
                          total_documentos=total_documentos,
                          documentos_vencidos=documentos_vencidos,
                          documentos_proximos=documentos_proximos)

# Rotas para Pessoas
@admin_bp.route('/pessoas')
@login_required
def listar_pessoas():
    """Lista todas as pessoas cadastradas."""
    pessoas = Pessoa.query.all()
    return render_template('admin/pessoas/listar.html', pessoas=pessoas)

@admin_bp.route('/pessoas/nova', methods=['GET', 'POST'])
@login_required
def nova_pessoa():
    """Cadastra uma nova pessoa."""
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf_cnpj = request.form.get('cpf_cnpj')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        endereco = request.form.get('endereco')
        
        # Validação básica
        if not nome or not cpf_cnpj:
            flash('Nome e CPF/CNPJ são obrigatórios.', 'danger')
            return render_template('admin/pessoas/form.html')
        
        # Verificar se já existe pessoa com o mesmo CPF/CNPJ
        pessoa_existente = Pessoa.query.filter_by(cpf_cnpj=cpf_cnpj).first()
        if pessoa_existente:
            flash(f'Já existe uma pessoa cadastrada com o CPF/CNPJ {cpf_cnpj}.', 'danger')
            return render_template('admin/pessoas/form.html')
        
        # Criar nova pessoa
        nova_pessoa = Pessoa(
            nome=nome,
            cpf_cnpj=cpf_cnpj,
            email=email,
            telefone=telefone,
            endereco=endereco
        )
        
        db.session.add(nova_pessoa)
        db.session.commit()
        
        flash(f'Pessoa {nome} cadastrada com sucesso!', 'success')
        return redirect(url_for('admin.listar_pessoas'))
    
    return render_template('admin/pessoas/form.html')

@admin_bp.route('/pessoas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_pessoa(id):
    """Edita uma pessoa existente."""
    pessoa = Pessoa.query.get_or_404(id)
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf_cnpj = request.form.get('cpf_cnpj')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        endereco = request.form.get('endereco')
        
        # Validação básica
        if not nome or not cpf_cnpj:
            flash('Nome e CPF/CNPJ são obrigatórios.', 'danger')
            return render_template('admin/pessoas/form.html', pessoa=pessoa)
        
        # Verificar se já existe outra pessoa com o mesmo CPF/CNPJ
        pessoa_existente = Pessoa.query.filter_by(cpf_cnpj=cpf_cnpj).first()
        if pessoa_existente and pessoa_existente.id != pessoa.id:
            flash(f'Já existe outra pessoa cadastrada com o CPF/CNPJ {cpf_cnpj}.', 'danger')
            return render_template('admin/pessoas/form.html', pessoa=pessoa)
        
        # Atualizar pessoa
        pessoa.nome = nome
        pessoa.cpf_cnpj = cpf_cnpj
        pessoa.email = email
        pessoa.telefone = telefone
        pessoa.endereco = endereco
        
        db.session.commit()
        
        flash(f'Pessoa {nome} atualizada com sucesso!', 'success')
        return redirect(url_for('admin.listar_pessoas'))
    
    return render_template('admin/pessoas/form.html', pessoa=pessoa)

@admin_bp.route('/pessoas/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_pessoa(id):
    """Exclui uma pessoa do sistema."""
    pessoa = Pessoa.query.get_or_404(id)
    
    # Verificar se a pessoa tem fazendas associadas
    if pessoa.fazendas:
        flash(f'Não é possível excluir a pessoa {pessoa.nome} pois ela possui fazendas associadas.', 'danger')
        return redirect(url_for('admin.listar_pessoas'))
    
    # Verificar se a pessoa tem documentos associados
    if hasattr(pessoa, 'documentos') and pessoa.documentos:
        flash(f'Não é possível excluir a pessoa {pessoa.nome} pois ela possui documentos associados.', 'danger')
        return redirect(url_for('admin.listar_pessoas'))
    
    nome = pessoa.nome
    db.session.delete(pessoa)
    db.session.commit()
    
    flash(f'Pessoa {nome} excluída com sucesso!', 'success')
    return redirect(url_for('admin.listar_pessoas'))

@admin_bp.route('/pessoas/<int:id>/fazendas')
@login_required
def listar_fazendas_pessoa(id):
    """Lista as fazendas associadas a uma pessoa."""
    pessoa = Pessoa.query.get_or_404(id)
    return render_template('admin/pessoas/fazendas.html', pessoa=pessoa)

@admin_bp.route('/pessoas/<int:pessoa_id>/associar-fazenda', methods=['GET', 'POST'])
@login_required
def associar_fazenda_pessoa(pessoa_id):
    """Associa uma fazenda a uma pessoa."""
    pessoa = Pessoa.query.get_or_404(pessoa_id)
    
    # Obter fazendas que ainda não estão associadas a esta pessoa
    fazendas_associadas = [f.id for f in pessoa.fazendas]
    fazendas_disponiveis = Fazenda.query.filter(~Fazenda.id.in_(fazendas_associadas)).all() if fazendas_associadas else Fazenda.query.all()
    
    if request.method == 'POST':
        fazenda_id = request.form.get('fazenda_id')
        
        if not fazenda_id:
            flash('Selecione uma fazenda para associar.', 'danger')
            return render_template('admin/pessoas/associar_fazenda.html', pessoa=pessoa, fazendas=fazendas_disponiveis)
        
        fazenda = Fazenda.query.get_or_404(fazenda_id)
        
        # Verificar se já está associada
        if fazenda in pessoa.fazendas:
            flash(f'A fazenda {fazenda.nome} já está associada a esta pessoa.', 'warning')
            return redirect(url_for('admin.listar_fazendas_pessoa', id=pessoa.id))
        
        # Associar fazenda à pessoa
        pessoa.fazendas.append(fazenda)
        db.session.commit()
        
        flash(f'Fazenda {fazenda.nome} associada com sucesso à pessoa {pessoa.nome}!', 'success')
        return redirect(url_for('admin.listar_fazendas_pessoa', id=pessoa.id))
    
    return render_template('admin/pessoas/associar_fazenda.html', pessoa=pessoa, fazendas=fazendas_disponiveis)

@admin_bp.route('/pessoas/<int:pessoa_id>/desassociar-fazenda/<int:fazenda_id>', methods=['POST'])
@login_required
def desassociar_fazenda_pessoa(pessoa_id, fazenda_id):
    """Desassocia uma fazenda de uma pessoa."""
    pessoa = Pessoa.query.get_or_404(pessoa_id)
    fazenda = Fazenda.query.get_or_404(fazenda_id)
    
    if fazenda not in pessoa.fazendas:
        flash(f'A fazenda {fazenda.nome} não está associada a esta pessoa.', 'warning')
        return redirect(url_for('admin.listar_fazendas_pessoa', id=pessoa.id))
    
    pessoa.fazendas.remove(fazenda)
    db.session.commit()
    
    flash(f'Fazenda {fazenda.nome} desassociada com sucesso da pessoa {pessoa.nome}!', 'success')
    return redirect(url_for('admin.listar_fazendas_pessoa', id=pessoa.id))

# Rotas para Fazendas
@admin_bp.route('/fazendas')
@login_required
def listar_fazendas():
    """Lista todas as fazendas cadastradas."""
    fazendas = Fazenda.query.all()
    return render_template('admin/fazendas/listar.html', fazendas=fazendas)

@admin_bp.route('/fazendas/nova', methods=['GET', 'POST'])
@login_required
def nova_fazenda():
    """Cadastra uma nova fazenda."""
    if request.method == 'POST':
        nome = request.form.get('nome')
        matricula = request.form.get('matricula')
        tamanho_total = request.form.get('tamanho_total')
        area_consolidada = request.form.get('area_consolidada')
        tipo_posse = request.form.get('tipo_posse')
        municipio = request.form.get('municipio')
        estado = request.form.get('estado')
        recibo_car = request.form.get('recibo_car')
        
        # Validação básica
        if not nome or not matricula or not tamanho_total or not area_consolidada or not tipo_posse or not municipio or not estado:
            flash('Todos os campos com * são obrigatórios.', 'danger')
            return render_template('admin/fazendas/form.html', tipos_posse=TipoPosse)
        
        # Verificar se já existe fazenda com a mesma matrícula
        fazenda_existente = Fazenda.query.filter_by(matricula=matricula).first()
        if fazenda_existente:
            flash(f'Já existe uma fazenda cadastrada com a matrícula {matricula}.', 'danger')
            return render_template('admin/fazendas/form.html', tipos_posse=TipoPosse)
        
        # Converter valores para float
        try:
            tamanho_total = float(tamanho_total)
            area_consolidada = float(area_consolidada)
        except ValueError:
            flash('Os valores de tamanho devem ser numéricos.', 'danger')
            return render_template('admin/fazendas/form.html', tipos_posse=TipoPosse)
        
        # Validar tamanhos
        if area_consolidada > tamanho_total:
            flash('A área consolidada não pode ser maior que o tamanho total.', 'danger')
            return render_template('admin/fazendas/form.html', tipos_posse=TipoPosse)
        
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
            recibo_car=recibo_car
        )
        
        db.session.add(nova_fazenda)
        db.session.commit()
        
        flash(f'Fazenda {nome} cadastrada com sucesso!', 'success')
        return redirect(url_for('admin.listar_fazendas'))
    
    return render_template('admin/fazendas/form.html', tipos_posse=TipoPosse)

@admin_bp.route('/fazendas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_fazenda(id):
    """Edita uma fazenda existente."""
    fazenda = Fazenda.query.get_or_404(id)
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        matricula = request.form.get('matricula')
        tamanho_total = request.form.get('tamanho_total')
        area_consolidada = request.form.get('area_consolidada')
        tipo_posse = request.form.get('tipo_posse')
        municipio = request.form.get('municipio')
        estado = request.form.get('estado')
        recibo_car = request.form.get('recibo_car')
        
        # Validação básica
        if not nome or not matricula or not tamanho_total or not area_consolidada or not tipo_posse or not municipio or not estado:
            flash('Todos os campos com * são obrigatórios.', 'danger')
            return render_template('admin/fazendas/form.html', fazenda=fazenda, tipos_posse=TipoPosse)
        
        # Verificar se já existe outra fazenda com a mesma matrícula
        fazenda_existente = Fazenda.query.filter_by(matricula=matricula).first()
        if fazenda_existente and fazenda_existente.id != fazenda.id:
            flash(f'Já existe outra fazenda cadastrada com a matrícula {matricula}.', 'danger')
            return render_template('admin/fazendas/form.html', fazenda=fazenda, tipos_posse=TipoPosse)
        
        # Converter valores para float
        try:
            tamanho_total = float(tamanho_total)
            area_consolidada = float(area_consolidada)
        except ValueError:
            flash('Os valores de tamanho devem ser numéricos.', 'danger')
            return render_template('admin/fazendas/form.html', fazenda=fazenda, tipos_posse=TipoPosse)
        
        # Validar tamanhos
        if area_consolidada > tamanho_total:
            flash('A área consolidada não pode ser maior que o tamanho total.', 'danger')
            return render_template('admin/fazendas/form.html', fazenda=fazenda, tipos_posse=TipoPosse)
        
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
        
        flash(f'Fazenda {nome} atualizada com sucesso!', 'success')
        return redirect(url_for('admin.listar_fazendas'))
    
    return render_template('admin/fazendas/form.html', fazenda=fazenda, tipos_posse=TipoPosse)

@admin_bp.route('/fazendas/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_fazenda(id):
    """Exclui uma fazenda do sistema."""
    fazenda = Fazenda.query.get_or_404(id)
    
    # Verificar se a fazenda tem documentos associados
    if fazenda.documentos:
        flash(f'Não é possível excluir a fazenda {fazenda.nome} pois ela possui documentos associados.', 'danger')
        return redirect(url_for('admin.listar_fazendas'))
    
    # Remover associações com pessoas
    for pessoa in fazenda.pessoas:
        pessoa.fazendas.remove(fazenda)
    
    nome = fazenda.nome
    db.session.delete(fazenda)
    db.session.commit()
    
    flash(f'Fazenda {nome} excluída com sucesso!', 'success')
    return redirect(url_for('admin.listar_fazendas'))

@admin_bp.route('/fazendas/<int:id>/documentos')
@login_required
def listar_documentos_fazenda(id):
    """Lista os documentos associados a uma fazenda."""
    fazenda = Fazenda.query.get_or_404(id)
    documentos = Documento.query.filter_by(fazenda_id=id).all()
    return render_template('admin/fazendas/documentos.html', fazenda=fazenda, documentos=documentos)

# Rotas para Documentos
@admin_bp.route('/documentos')
@login_required
def listar_documentos():
    """Lista todos os documentos cadastrados."""
    documentos = Documento.query.all()
    return render_template('admin/documentos/listar.html', documentos=documentos)

@admin_bp.route('/documentos/novo', methods=['GET', 'POST'])
@login_required
def novo_documento():
    """Cadastra um novo documento."""
    fazendas = Fazenda.query.all()
    pessoas = Pessoa.query.all()
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo = request.form.get('tipo')
        tipo_personalizado = request.form.get('tipo_personalizado')
        data_emissao = request.form.get('data_emissao')
        data_vencimento = request.form.get('data_vencimento')
        emails_notificacao = request.form.get('emails_notificacao')
        tipo_entidade = request.form.get('tipo_entidade')
        fazenda_id = request.form.get('fazenda_id') if tipo_entidade == 'FAZENDA' else None
        pessoa_id = request.form.get('pessoa_id') if tipo_entidade == 'PESSOA' else None
        
        # Obter múltiplos prazos de notificação
        prazos_notificacao = request.form.getlist('prazo_notificacao[]')
        if not prazos_notificacao:
            prazos_notificacao = []  # Lista vazia se nenhum prazo selecionado
        else:
            prazos_notificacao = [int(prazo) for prazo in prazos_notificacao]
        
        # Validação básica
        if not nome or not tipo or not data_emissao:
            flash('Todos os campos com * são obrigatórios.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        
        # Validação da entidade relacionada
        if tipo_entidade == 'FAZENDA' and not fazenda_id:
            flash('Selecione uma fazenda/área para relacionar o documento.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        elif tipo_entidade == 'PESSOA' and not pessoa_id:
            flash('Selecione uma pessoa para relacionar o documento.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        
        # Validação do tipo personalizado
        if tipo == 'Outros' and not tipo_personalizado:
            flash('Para o tipo "Outros", é necessário informar o tipo personalizado.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        
        # Converter datas
        try:
            data_emissao = datetime.datetime.strptime(data_emissao, '%Y-%m-%d').date()
            if data_vencimento:
                data_vencimento = datetime.datetime.strptime(data_vencimento, '%Y-%m-%d').date()
            else:
                data_vencimento = None
        except ValueError:
            flash('Formato de data inválido.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        
        # Criar novo documento
        novo_documento = Documento(
            nome=nome,
            tipo=TipoDocumento(tipo),
            tipo_personalizado=tipo_personalizado if tipo == 'Outros' else None,
            data_emissao=data_emissao,
            data_vencimento=data_vencimento,
            tipo_entidade=TipoEntidade.FAZENDA if tipo_entidade == 'FAZENDA' else TipoEntidade.PESSOA,
            fazenda_id=int(fazenda_id) if fazenda_id else None,
            pessoa_id=int(pessoa_id) if pessoa_id else None
        )
        
        # Definir emails para notificação
        novo_documento.emails_notificacao = emails_notificacao
        
        # Definir prazos de notificação
        novo_documento.prazos_notificacao = prazos_notificacao
        
        db.session.add(novo_documento)
        db.session.commit()
        
        flash(f'Documento {nome} cadastrado com sucesso!', 'success')
        return redirect(url_for('admin.listar_documentos'))
    
    return render_template('admin/documentos/form.html', 
                          tipos_documento=TipoDocumento, 
                          fazendas=fazendas,
                          pessoas=pessoas)

@admin_bp.route('/documentos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_documento(id):
    """Edita um documento existente."""
    documento = Documento.query.get_or_404(id)
    fazendas = Fazenda.query.all()
    pessoas = Pessoa.query.all()
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo = request.form.get('tipo')
        tipo_personalizado = request.form.get('tipo_personalizado')
        data_emissao = request.form.get('data_emissao')
        data_vencimento = request.form.get('data_vencimento')
        emails_notificacao = request.form.get('emails_notificacao')
        tipo_entidade = request.form.get('tipo_entidade')
        fazenda_id = request.form.get('fazenda_id') if tipo_entidade == 'FAZENDA' else None
        pessoa_id = request.form.get('pessoa_id') if tipo_entidade == 'PESSOA' else None
        
        # Obter múltiplos prazos de notificação
        prazos_notificacao = request.form.getlist('prazo_notificacao[]')
        if not prazos_notificacao:
            prazos_notificacao = []  # Lista vazia se nenhum prazo selecionado
        else:
            prazos_notificacao = [int(prazo) for prazo in prazos_notificacao]
        
        # Validação básica
        if not nome or not tipo or not data_emissao:
            flash('Todos os campos com * são obrigatórios.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  documento=documento,
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        
        # Validação da entidade relacionada
        if tipo_entidade == 'FAZENDA' and not fazenda_id:
            flash('Selecione uma fazenda/área para relacionar o documento.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  documento=documento,
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        elif tipo_entidade == 'PESSOA' and not pessoa_id:
            flash('Selecione uma pessoa para relacionar o documento.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  documento=documento,
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        
        # Validação do tipo personalizado
        if tipo == 'Outros' and not tipo_personalizado:
            flash('Para o tipo "Outros", é necessário informar o tipo personalizado.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  documento=documento,
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        
        # Converter datas
        try:
            data_emissao = datetime.datetime.strptime(data_emissao, '%Y-%m-%d').date()
            if data_vencimento:
                data_vencimento = datetime.datetime.strptime(data_vencimento, '%Y-%m-%d').date()
            else:
                data_vencimento = None
        except ValueError:
            flash('Formato de data inválido.', 'danger')
            return render_template('admin/documentos/form.html', 
                                  documento=documento,
                                  tipos_documento=TipoDocumento, 
                                  fazendas=fazendas,
                                  pessoas=pessoas)
        
        # Atualizar documento
        documento.nome = nome
        documento.tipo = TipoDocumento(tipo)
        documento.tipo_personalizado = tipo_personalizado if tipo == 'Outros' else None
        documento.data_emissao = data_emissao
        documento.data_vencimento = data_vencimento
        documento.tipo_entidade = TipoEntidade.FAZENDA if tipo_entidade == 'FAZENDA' else TipoEntidade.PESSOA
        
        # Atualizar relacionamentos
        if tipo_entidade == 'FAZENDA':
            documento.fazenda_id = int(fazenda_id)
            documento.pessoa_id = None
        else:
            documento.fazenda_id = None
            documento.pessoa_id = int(pessoa_id)
        
        # Atualizar emails para notificação
        documento.emails_notificacao = emails_notificacao
        
        # Atualizar prazos de notificação
        documento.prazos_notificacao = prazos_notificacao
        
        db.session.commit()
        
        flash(f'Documento {nome} atualizado com sucesso!', 'success')
        return redirect(url_for('admin.listar_documentos'))
    
    return render_template('admin/documentos/form.html', 
                          documento=documento,
                          tipos_documento=TipoDocumento, 
                          fazendas=fazendas,
                          pessoas=pessoas)

@admin_bp.route('/documentos/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_documento(id):
    """Exclui um documento do sistema."""
    documento = Documento.query.get_or_404(id)
    
    nome = documento.nome
    db.session.delete(documento)
    db.session.commit()
    
    flash(f'Documento {nome} excluído com sucesso!', 'success')
    return redirect(url_for('admin.listar_documentos'))

@admin_bp.route('/documentos/vencidos')
@login_required
def listar_documentos_vencidos():
    """Lista documentos vencidos ou próximos do vencimento."""
    hoje = datetime.date.today()
    
    # Documentos já vencidos
    documentos_vencidos = Documento.query.filter(
        Documento.data_vencimento < hoje
    ).order_by(Documento.data_vencimento).all()
    
    # Documentos próximos do vencimento (30 dias)
    data_limite = hoje + datetime.timedelta(days=30)
    documentos_proximos = Documento.query.filter(
        Documento.data_vencimento >= hoje,
        Documento.data_vencimento <= data_limite
    ).order_by(Documento.data_vencimento).all()
    
    return render_template('admin/documentos/vencidos.html', 
                          documentos_vencidos=documentos_vencidos,
                          documentos_proximos=documentos_proximos)

@admin_bp.route('/documentos/notificacoes', methods=['GET', 'POST'])
@login_required
def notificacoes_documentos():
    """Gerencia notificações de vencimento de documentos."""
    documentos_por_prazo = verificar_documentos_vencendo()
    
    if request.method == 'POST':
        # Lógica para enviar notificações manualmente
        # Implementação futura
        flash('Notificações enviadas com sucesso!', 'success')
        return redirect(url_for('admin.notificacoes_documentos'))
    
    return render_template('admin/documentos/notificacoes.html', 
                          documentos_por_prazo=documentos_por_prazo)

@admin_bp.route('/testar-email', methods=['POST'])
@login_required
def testar_email():
    """Envia um e-mail de teste para verificar a configuração."""
    emails = request.form.get('emails', '')
    
    if not emails:
        return jsonify({'sucesso': False, 'mensagem': 'Nenhum e-mail informado.'})
    
    # Converter string de emails para lista
    lista_emails = [email.strip() for email in emails.split(',') if email.strip()]
    
    if not lista_emails:
        return jsonify({'sucesso': False, 'mensagem': 'Formato de e-mail inválido.'})
    
    # Enviar e-mail de teste
    sucesso = EmailService().enviar_email_teste(lista_emails)
    mensagem = "E-mail de teste enviado com sucesso." if sucesso else "Falha ao enviar e-mail de teste. Verifique as configurações."
    
    return jsonify({'sucesso': sucesso, 'mensagem': mensagem})