#/src/routes/endividamento.py
# Rotas para gerenciamento de endividamentos
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import and_, or_
from src.models.db import db
from src.models.endividamento import Endividamento, EndividamentoFazenda, Parcela
from src.models.notificacao_endividamento import NotificacaoEndividamento
from src.models.pessoa import Pessoa
from src.models.fazenda import Fazenda
from src.forms.endividamento import EndividamentoForm, FiltroEndividamentoForm
from src.forms.notificacao_endividamento import NotificacaoEndividamentoForm
from src.utils.validators import validate_required_fields, sanitize_input
from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
from datetime import datetime, date
import json

endividamento_bp = Blueprint('endividamento', __name__, url_prefix='/endividamentos')

@endividamento_bp.route('/')
def listar():
    """Lista todos os endividamentos com filtros opcionais"""
    form_filtro = FiltroEndividamentoForm()
    
    # Preencher opções dos selects
    form_filtro.pessoa_id.choices = [(0, 'Todas as pessoas')] + [(p.id, p.nome) for p in Pessoa.query.all()]
    form_filtro.fazenda_id.choices = [(0, 'Todas as fazendas')] + [(f.id, f.nome) for f in Fazenda.query.all()]
    
    # Construir query base
    query = Endividamento.query
    
    # Aplicar filtros se fornecidos
    if request.args.get('banco'):
        query = query.filter(Endividamento.banco.ilike(f"%{request.args.get('banco')}%"))
    
    if request.args.get('pessoa_id') and int(request.args.get('pessoa_id')) > 0:
        query = query.join(Endividamento.pessoas).filter(Pessoa.id == int(request.args.get('pessoa_id')))
    
    if request.args.get('fazenda_id') and int(request.args.get('fazenda_id')) > 0:
        query = query.join(Endividamento.fazenda_vinculos).filter(EndividamentoFazenda.fazenda_id == int(request.args.get('fazenda_id')))
    
    if request.args.get('data_inicio'):
        data_inicio = datetime.strptime(request.args.get('data_inicio'), '%Y-%m-%d').date()
        query = query.filter(Endividamento.data_emissao >= data_inicio)
    
    if request.args.get('data_fim'):
        data_fim = datetime.strptime(request.args.get('data_fim'), '%Y-%m-%d').date()
        query = query.filter(Endividamento.data_emissao <= data_fim)
    
    if request.args.get('vencimento_inicio'):
        venc_inicio = datetime.strptime(request.args.get('vencimento_inicio'), '%Y-%m-%d').date()
        query = query.filter(Endividamento.data_vencimento_final >= venc_inicio)
    
    if request.args.get('vencimento_fim'):
        venc_fim = datetime.strptime(request.args.get('vencimento_fim'), '%Y-%m-%d').date()
        query = query.filter(Endividamento.data_vencimento_final <= venc_fim)
    
    # Ordenar por data de vencimento final
    endividamentos = query.order_by(Endividamento.data_vencimento_final.asc()).all()
    
    # Passando form_filtro para o template
    return render_template(
        'admin/endividamentos/listar.html',
        endividamentos=endividamentos,
        form_filtro=form_filtro,  # Passando o formulário para o template
        date=date  # ✅ passa o objeto date para o template
    )

@endividamento_bp.route('/novo', methods=['GET', 'POST'])
def novo():
    """Cadastra um novo endividamento"""
    form = EndividamentoForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # Criar novo endividamento
                endividamento = Endividamento(
                    banco=sanitize_input(form.banco.data),
                    numero_proposta=sanitize_input(form.numero_proposta.data),
                    data_emissao=form.data_emissao.data,
                    data_vencimento_final=form.data_vencimento_final.data,
                    taxa_juros=form.taxa_juros.data,
                    tipo_taxa_juros=form.tipo_taxa_juros.data,
                    prazo_carencia=form.prazo_carencia.data,
                    valor_operacao=form.valor_operacao.data
                )
                
                db.session.add(endividamento)
                db.session.flush()  # Para obter o ID
                
                # Processar pessoas selecionadas
                pessoas_ids = request.form.getlist('pessoas_ids')
                if pessoas_ids:
                    pessoas = Pessoa.query.filter(Pessoa.id.in_(pessoas_ids)).all()
                    endividamento.pessoas = pessoas
                
                # Processar vínculos com fazendas (objeto do crédito)
                objetos_credito_str = json.loads(request.form.get('objetos_credito') or '[]')
                if objetos_credito_str:
                    objetos_credito = json.loads(objetos_credito_str)
                else:
                    objetos_credito = []
                for obj in objetos_credito:
                    vinculo = EndividamentoFazenda(
                        endividamento_id=endividamento.id,
                        fazenda_id=obj.get('fazenda_id') if obj.get('fazenda_id') else None,
                        hectares=obj.get('hectares'),
                        tipo='objeto_credito',
                        descricao=sanitize_input(obj.get('descricao'))
                    )
                    db.session.add(vinculo)
                
                # Processar garantias
                garantias = json.loads(request.form.get('garantias') or '[]')
                for gar in garantias:
                    vinculo = EndividamentoFazenda(
                        endividamento_id=endividamento.id,
                        fazenda_id=gar.get('fazenda_id') if gar.get('fazenda_id') else None,
                        hectares=gar.get('hectares'),
                        tipo='garantia',
                        descricao=sanitize_input(gar.get('descricao'))
                    )
                    db.session.add(vinculo)
                
                # Processar parcelas
                parcelas = json.loads(request.form.get('parcelas') or '[]')
                for parc in parcelas:
                    parcela = Parcela(
                        endividamento_id=endividamento.id,
                        data_vencimento=datetime.strptime(parc['data_vencimento'], '%Y-%m-%d').date(),
                        valor=float(parc['valor'])
                    )
                    db.session.add(parcela)
                
                db.session.commit()
                flash('Endividamento cadastrado com sucesso!', 'success')
                return redirect(url_for('endividamento.listar'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao cadastrar endividamento: {str(e)}', 'danger')
        else:
            flash('Erro na validação do formulário. Verifique os dados informados.', 'danger')
    
    # Carregar dados para os selects
    pessoas = Pessoa.query.all()
    fazendas = Fazenda.query.all()
    
    return render_template('admin/endividamentos/form.html', 
                         form=form, 
                         pessoas=pessoas, 
                         fazendas=fazendas,
                         endividamento=None)

@endividamento_bp.route('/<int:id>')
def visualizar(id):
    """Visualiza detalhes de um endividamento"""
    endividamento = Endividamento.query.get_or_404(id)
    return render_template(
    'admin/endividamentos/visualizar.html',
    endividamento=endividamento,
    date=date  # <-- Passe o objeto date para o template!
)

@endividamento_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    """Edita um endividamento existente"""
    endividamento = Endividamento.query.get_or_404(id)
    form = EndividamentoForm(obj=endividamento)
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # Atualizar dados básicos
                endividamento.banco = sanitize_input(form.banco.data)
                endividamento.numero_proposta = sanitize_input(form.numero_proposta.data)
                endividamento.data_emissao = form.data_emissao.data
                endividamento.data_vencimento_final = form.data_vencimento_final.data
                endividamento.taxa_juros = form.taxa_juros.data
                endividamento.tipo_taxa_juros = form.tipo_taxa_juros.data
                endividamento.prazo_carencia = form.prazo_carencia.data
                endividamento.valor_operacao = form.valor_operacao.data
                
                # Atualizar pessoas
                pessoas_ids = request.form.getlist('pessoas_ids')
                if pessoas_ids:
                    pessoas = Pessoa.query.filter(Pessoa.id.in_(pessoas_ids)).all()
                    endividamento.pessoas = pessoas
                else:
                    endividamento.pessoas = []
                
                # Remover vínculos existentes
                EndividamentoFazenda.query.filter_by(endividamento_id=id).delete()
                
                # Recriar vínculos com fazendas
                objetos_credito_str = request.form.get('objetos_credito')
                if objetos_credito_str:
                    objetos_credito = json.loads(objetos_credito_str)
                else:
                    objetos_credito = []
                for obj in objetos_credito:
                    vinculo = EndividamentoFazenda(
                        endividamento_id=endividamento.id,
                        fazenda_id=obj.get('fazenda_id') if obj.get('fazenda_id') else None,
                        hectares=obj.get('hectares'),
                        tipo='objeto_credito',
                        descricao=sanitize_input(obj.get('descricao'))
                    )
                    db.session.add(vinculo)
                
                garantias = json.loads(request.form.get('garantias', '[]')  or '[]')
                for gar in garantias:
                    vinculo = EndividamentoFazenda(
                        endividamento_id=endividamento.id,
                        fazenda_id=gar.get('fazenda_id') if gar.get('fazenda_id') else None,
                        hectares=gar.get('hectares'),
                        tipo='garantia',
                        descricao=sanitize_input(gar.get('descricao'))
                    )
                    db.session.add(vinculo)
                
                # Remover parcelas existentes
                Parcela.query.filter_by(endividamento_id=id).delete()
                
                # Recriar parcelas
                parcelas  = json.loads(request.form.get('parcelas') or '[]')
                for parc in parcelas:
                    parcela = Parcela(
                        endividamento_id=endividamento.id,
                        data_vencimento=datetime.strptime(parc['data_vencimento'], '%Y-%m-%d').date(),
                        valor=float(parc['valor'])
                    )
                    db.session.add(parcela)
                
                db.session.commit()
                flash('Endividamento atualizado com sucesso!', 'success')
                return redirect(url_for('endividamento.visualizar', id=id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar endividamento: {str(e)}', 'danger')
        else:
            flash('Erro na validação do formulário. Verifique os dados informados.', 'danger')
    
    # Carregar dados para os selects
    pessoas = Pessoa.query.all()
    fazendas = Fazenda.query.all()
    
    return render_template('admin/endividamentos/form.html', 
                         form=form, 
                         pessoas=pessoas, 
                         fazendas=fazendas,
                         endividamento=endividamento)

@endividamento_bp.route('/<int:id>/excluir', methods=['POST'])
def excluir(id):
    """Exclui um endividamento"""
    endividamento = Endividamento.query.get_or_404(id)
    
    try:
        db.session.delete(endividamento)
        db.session.commit()
        flash('Endividamento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir endividamento: {str(e)}', 'danger')
    
    return redirect(url_for('endividamento.listar'))

@endividamento_bp.route('/vencimentos')
def vencimentos():
    """Lista parcelas próximas do vencimento"""
    hoje = date.today()
    
    # Parcelas vencidas
    parcelas_vencidas = Parcela.query.filter(
        Parcela.data_vencimento < hoje,
        Parcela.pago == False
    ).order_by(Parcela.data_vencimento.asc()).all()
    
    # Parcelas vencendo nos próximos 30 dias
    from datetime import timedelta
    data_limite = hoje + timedelta(days=30)
    
    parcelas_a_vencer = Parcela.query.filter(
        and_(
            Parcela.data_vencimento >= hoje,
            Parcela.data_vencimento <= data_limite,
            Parcela.pago == False
        )
    ).order_by(Parcela.data_vencimento.asc()).all()
    
    return render_template('admin/endividamentos/vencimentos.html',
                         parcelas_vencidas=parcelas_vencidas,
                         parcelas_a_vencer=parcelas_a_vencer)

@endividamento_bp.route('/parcela/<int:id>/pagar', methods=['POST'])
def pagar_parcela(id):
    """Marca uma parcela como paga"""
    parcela = Parcela.query.get_or_404(id)
    
    try:
        parcela.pago = True
        parcela.data_pagamento = date.today()
        parcela.valor_pago = request.form.get('valor_pago', parcela.valor)
        parcela.observacoes = sanitize_input(request.form.get('observacoes', ''))
        
        db.session.commit()
        flash('Parcela marcada como paga!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao marcar parcela como paga: {str(e)}', 'danger')
    
    return redirect(url_for('endividamento.vencimentos'))

@endividamento_bp.route('/api/fazendas/<int:pessoa_id>')
def api_fazendas_pessoa(pessoa_id):
    """API para obter fazendas de uma pessoa"""
    pessoa = Pessoa.query.get_or_404(pessoa_id)
    fazendas = [{'id': f.id, 'nome': f.nome, 'tamanho_total': float(f.tamanho_total)} for f in pessoa.fazendas]
    return jsonify(fazendas)



@endividamento_bp.route('/buscar-pessoas')
def buscar_pessoas():
    """Endpoint para busca AJAX de pessoas"""
    termo = request.args.get('q', '').strip()
    
    if len(termo) < 2:
        return jsonify([])  # Retorne um array direto
    
    pessoas = Pessoa.query.filter(
        or_(
            Pessoa.nome.ilike(f'%{termo}%'),
            Pessoa.cpf_cnpj.ilike(f'%{termo}%')
        )
    ).limit(10).all()
    
    resultado = [{
        'id': pessoa.id,
        'nome': pessoa.nome,
        'cpf_cnpj': pessoa.cpf_cnpj,
        'cpf_cnpj_formatado': pessoa.formatar_cpf_cnpj()  # Só se existir
    } for pessoa in pessoas]
    
    return jsonify(resultado)  # <-- ARRAY DIRETO!



@endividamento_bp.route('/<int:id>/notificacoes', methods=['GET', 'POST'])
def configurar_notificacoes(id):
    """Configura notificações para um endividamento"""
    endividamento = Endividamento.query.get_or_404(id)
    form = NotificacaoEndividamentoForm()
    service = NotificacaoEndividamentoService()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # Processar lista de e-mails
                emails = [email.strip() for email in form.emails.data.split('\n') if email.strip()]
                
                # Configurar notificação
                sucesso = service.configurar_notificacao(
                    endividamento_id=id,
                    emails=emails,
                    ativo=form.ativo.data
                )
                
                if sucesso:
                    flash('Configurações de notificação salvas com sucesso!', 'success')
                    return redirect(url_for('endividamento.visualizar', id=id))
                else:
                    flash('Erro ao salvar configurações de notificação.', 'danger')
                    
            except Exception as e:
                flash(f'Erro ao processar configurações: {str(e)}', 'danger')
        else:
            flash('Erro na validação do formulário. Verifique os dados informados.', 'danger')
    
    # Carregar configuração existente
    configuracao = service.obter_configuracao(id)
    if configuracao['emails']:
        form.emails.data = '\n'.join(configuracao['emails'])
        form.ativo.data = configuracao['ativo']
    
    # Carregar histórico
    historico = service.obter_historico(id)
    
    return render_template('admin/endividamentos/notificacoes.html',
                         endividamento=endividamento,
                         form=form,
                         historico=historico)

@endividamento_bp.route('/api/processar-notificacoes', methods=['POST'])
def processar_notificacoes():
    """API para processar notificações manualmente (para testes)"""
    try:
        service = NotificacaoEndividamentoService()
        notificacoes_enviadas = service.verificar_e_enviar_notificacoes()
        
        return jsonify({
            'sucesso': True,
            'notificacoes_enviadas': notificacoes_enviadas,
            'mensagem': f'{notificacoes_enviadas} notificações foram enviadas.'
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

