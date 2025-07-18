# /src/routes/endividamento.py

"""
Rotas para gerenciamento de endividamentos.
Inclui operações CRUD, configuração de notificações, vinculação de áreas, 
e APIs para processamento de endividamentos.
"""

import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, current_app, abort
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload

from src.forms.endividamento import EndividamentoForm, FiltroEndividamentoForm
from src.forms.notificacao_endividamento import NotificacaoEndividamentoForm
from src.models.db import db
from src.models.endividamento import Endividamento, EndividamentoFazenda, Parcela
from src.models.fazenda import Fazenda
from src.models.notificacao_endividamento import NotificacaoEndividamento, HistoricoNotificacao
from src.models.pessoa import Pessoa
from src.utils.notificacao_endividamento_service import notificacao_endividamento_service
from src.utils.validators import sanitize_input
from src.utils.notificacao_utils import calcular_proximas_notificacoes_programadas
from src.utils.performance import measure_performance, clear_related_cache
from src.utils.cache import cached
from src.utils.email_service import email_service

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
@measure_performance()
def add_areas_endividamento(id: int):
    """
    Vincula áreas a um endividamento.
    
    Args:
        id: ID do endividamento
        
    Espera JSON: {"areas": [{"area_id":..., "tipo":..., "hectares_utilizados":...}, ...]}
    
    Returns:
        Resposta JSON com mensagem de sucesso ou erro
    """
    try:
        # Validar existência do endividamento
        endividamento = Endividamento.query.get_or_404(id)
        
        data = request.get_json()
        if not data or 'areas' not in data:
            return jsonify({'error': 'Dados inválidos. Esperado: {"areas": [...]}'}), 400
        
        # Validar cada área antes de adicionar
        for area in data['areas']:
            if not area.get('area_id'):
                return jsonify({'error': 'Área não identificada (area_id ausente)'}), 400
                
            if area.get('hectares_utilizados'):
                ok, msg = validar_hectares_disponiveis(area['area_id'], area['hectares_utilizados'])
                if not ok:
                    return jsonify({'error': msg}), 400
        
        # Adicionar áreas validadas
        adicionar_areas_endividamento(id, data['areas'])
        
        # Limpar cache relacionado
        clear_related_cache("endividamento")
        
        return jsonify({
            "message": "Áreas vinculadas com sucesso.",
            "endividamento_id": id,
            "areas_vinculadas": len(data['areas'])
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Erro ao adicionar áreas ao endividamento {id}: {str(e)}")
        return jsonify({'error': f"Erro ao vincular áreas: {str(e)}"}), 500


@endividamento_bp.route("/<int:id>/areas", methods=["GET"])
@cached(timeout=300, key_prefix="endividamento_areas")
def listar_areas_endividamento(id: int):
    """
    Lista áreas vinculadas a um endividamento.
    
    Args:
        id: ID do endividamento
        
    Returns:
        Lista de áreas vinculadas em formato JSON
    """
    try:
        # Validar existência do endividamento
        endividamento = Endividamento.query.get_or_404(id)
        
        # Obter áreas vinculadas
        areas = get_areas_vinculadas(id)
        
        return jsonify({
            "endividamento_id": id,
            "nome_banco": endividamento.banco,
            "areas": areas,
            "total_areas": len(areas)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Erro ao listar áreas do endividamento {id}: {str(e)}")
        return jsonify({'error': f"Erro ao listar áreas: {str(e)}"}), 500


@endividamento_bp.route("/<int:endividamento_id>/area/<int:area_id>", methods=["DELETE"])
@measure_performance()
def desvincular_area(endividamento_id: int, area_id: int):
    """
    Desvincula uma área de um endividamento.
    
    Args:
        endividamento_id: ID do endividamento
        area_id: ID da área a ser desvinculada
        
    Returns:
        Mensagem de sucesso em formato JSON
    """
    try:
        # Validar existência do endividamento
        Endividamento.query.get_or_404(endividamento_id)
        
        # Remover vínculo
        remover_area_vinculo(endividamento_id, area_id)
        
        # Limpar cache relacionado
        clear_related_cache("endividamento")
        
        return jsonify({
            "message": "Área desvinculada com sucesso.",
            "endividamento_id": endividamento_id,
            "area_id": area_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Erro ao desvincular área {area_id} do endividamento {endividamento_id}: {str(e)}")
        return jsonify({'error': f"Erro ao desvincular área: {str(e)}"}), 500


# --- RESTANTE DAS ROTAS DO ENDIVIDAMENTO ---

@endividamento_bp.route("/")
@measure_performance()
def listar():
    """
    Lista todos os endividamentos com filtros opcionais.
    
    Suporta diversos filtros como banco, pessoa, fazenda, datas.
    
    Returns:
        Template renderizado com lista de endividamentos
    """
    try:
        form_filtro = FiltroEndividamentoForm()

        # Preencher opções dos selects
        form_filtro.pessoa_id.choices = [(0, "Todas as pessoas")] + [
            (p.id, p.nome) for p in Pessoa.query.all()
        ]
        form_filtro.fazenda_id.choices = [(0, "Todas as fazendas")] + [
            (f.id, f.nome) for f in Fazenda.query.all()
        ]

        # Construir consulta com filtros aplicados
        query = Endividamento.query

        # Filtros aplicados pela URL
        if request.args.get("banco"):
            termo_busca = request.args.get("banco")
            query = query.filter(
                Endividamento.banco.ilike(f"%{termo_busca}%")
            )

        if request.args.get("pessoa_id") and int(request.args.get("pessoa_id")) > 0:
            pessoa_id = int(request.args.get("pessoa_id"))
            query = query.join(Endividamento.pessoas).filter(
                Pessoa.id == pessoa_id
            )

        if request.args.get("fazenda_id") and int(request.args.get("fazenda_id")) > 0:
            fazenda_id = int(request.args.get("fazenda_id"))
            query = query.join(Endividamento.fazenda_vinculos).filter(
                EndividamentoFazenda.fazenda_id == fazenda_id
            )

        # Filtros de data de emissão
        if request.args.get("data_inicio"):
            try:
                data_inicio = datetime.strptime(
                    request.args.get("data_inicio"), "%Y-%m-%d"
                ).date()
                query = query.filter(Endividamento.data_emissao >= data_inicio)
            except ValueError:
                flash("Formato de data inválido para data início", "warning")

        if request.args.get("data_fim"):
            try:
                data_fim = datetime.strptime(
                    request.args.get("data_fim"), "%Y-%m-%d"
                ).date()
                query = query.filter(Endividamento.data_emissao <= data_fim)
            except ValueError:
                flash("Formato de data inválido para data fim", "warning")

        # Filtros de data de vencimento
        if request.args.get("vencimento_inicio"):
            try:
                venc_inicio = datetime.strptime(
                    request.args.get("vencimento_inicio"), "%Y-%m-%d"
                ).date()
                query = query.filter(Endividamento.data_vencimento_final >= venc_inicio)
            except ValueError:
                flash("Formato de data inválido para vencimento início", "warning")

        if request.args.get("vencimento_fim"):
            try:
                venc_fim = datetime.strptime(
                    request.args.get("vencimento_fim"), "%Y-%m-%d"
                ).date()
                query = query.filter(Endividamento.data_vencimento_final <= venc_fim)
            except ValueError:
                flash("Formato de data inválido para vencimento fim", "warning")
        
        # Carregar dados relacionados para evitar N+1 queries
        query = query.options(
            joinedload(Endividamento.pessoas),
            joinedload(Endividamento.fazenda_vinculos).joinedload(EndividamentoFazenda.fazenda)
        )

        # Ordenar por vencimento (mais próximo primeiro)
        endividamentos = query.order_by(Endividamento.data_vencimento_final.asc()).all()

        return render_template(
            "admin/endividamentos/listar.html",
            endividamentos=endividamentos,
            form_filtro=form_filtro,
            date=date,
            total_resultados=len(endividamentos),
            filtros_ativos=bool(request.args)
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao listar endividamentos: {str(e)}")
        flash(f"Erro ao carregar a lista de endividamentos: {str(e)}", "danger")
        return render_template(
            "admin/endividamentos/listar.html",
            endividamentos=[],
            form_filtro=FiltroEndividamentoForm(),
            date=date,
            erro=str(e)
        )


@endividamento_bp.route("/novo", methods=["GET", "POST"])
@measure_performance()
def novo():
    """
    Cadastra um novo endividamento.
    
    Suporta formulário HTML com dados complexos como objetos de crédito,
    garantias e parcelas.
    
    Returns:
        Formulário de cadastro ou redirecionamento após sucesso
    """
    form = EndividamentoForm()

    if request.method == "POST":
        if form.validate_on_submit():
            try:
                # Criar endividamento com os dados do formulário
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

                # Adicionar ao banco e obter ID
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
                            descricao=sanitize_input(obj.get("descricao", "")),
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
                            descricao=sanitize_input(gar.get("descricao", "")),
                        )
                        db.session.add(vinculo)

                # Processar parcelas
                parcelas = json.loads(request.form.get("parcelas") or "[]")
                for parc in parcelas:
                    if parc.get("data_vencimento") and parc.get("valor"):
                        try:
                            data_venc = datetime.strptime(
                                parc["data_vencimento"], "%Y-%m-%d"
                            ).date()
                            
                            parcela = Parcela(
                                endividamento_id=endividamento.id,
                                data_vencimento=data_venc,
                                valor=float(parc["valor"]),
                                pago=False
                            )
                            db.session.add(parcela)
                        except (ValueError, TypeError) as e:
                            current_app.logger.warning(f"Erro ao processar parcela: {str(e)}")

                # Salvar tudo no banco
                db.session.commit()
                
                # Criar notificações para o endividamento, se tiver vencimento
                if endividamento.data_vencimento_final:
                    try:
                        notificacao_endividamento_service._verificar_e_criar_notificacoes(endividamento)
                    except Exception as e:
                        current_app.logger.error(f"Erro ao criar notificações: {str(e)}")
                
                # Limpar cache relacionado
                clear_related_cache("endividamento")
                
                flash("Endividamento cadastrado com sucesso!", "success")
                return redirect(url_for("endividamento.visualizar", id=endividamento.id))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erro ao cadastrar endividamento: {str(e)}")
                flash(f"Erro ao cadastrar endividamento: {str(e)}", "danger")
        else:
            # Erros de validação do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Erro no campo {getattr(form, field).label.text}: {error}", "danger")

    # Carregar dados para preenchimento do formulário
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    fazendas = Fazenda.query.order_by(Fazenda.nome).all()

    return render_template(
        "admin/endividamentos/form.html",
        form=form,
        pessoas=pessoas,
        fazendas=fazendas,
        endividamento=None,
        data_atual=date.today().isoformat()
    )


@endividamento_bp.route("/<int:id>")
@measure_performance()
def visualizar(id: int):
    """
    Visualiza detalhes de um endividamento.
    
    Args:
        id: ID do endividamento
        
    Returns:
        Template renderizado com detalhes do endividamento
    """
    try:
        endividamento = Endividamento.query.get_or_404(id)
        
        # Serviço para notificações
        service = notificacao_endividamento_service
        
        # Obter próximas notificações usando o serviço
        proximas_notificacoes = service.obter_proximas_notificacoes(id)
        
        # Buscar notificações agendadas com dados completos
        notificacoes_agendadas = NotificacaoEndividamento.query.filter_by(
            endividamento_id=id,
            ativo=True
        ).order_by(NotificacaoEndividamento.data_envio).all()
        
        # Verificar se tem configuração de notificação
        tem_notificacao_config = NotificacaoEndividamento.query.filter_by(
            endividamento_id=id,
            tipo_notificacao='config',
            ativo=True
        ).first() is not None
        
        # Áreas vinculadas via utilitário
        areas_vinculadas = get_areas_vinculadas(endividamento.id)
        
        # Parcelas organizadas
        parcelas_pendentes = [p for p in endividamento.parcelas if not p.pago]
        parcelas_pagas = [p for p in endividamento.parcelas if p.pago]
        
        # Calcular totais para o dashboard
        valor_total = endividamento.valor_operacao or 0
        valor_pago = sum(p.valor_pago or p.valor for p in parcelas_pagas)
        valor_pendente = sum(p.valor for p in parcelas_pendentes)
        
        porcentagem_pago = (valor_pago / valor_total * 100) if valor_total > 0 else 0
        
        # Métricas para o dashboard
        dashboard = {
            "valor_total": valor_total,
            "valor_pago": valor_pago,
            "valor_pendente": valor_pendente,
            "porcentagem_pago": porcentagem_pago,
            "parcelas_total": len(endividamento.parcelas),
            "parcelas_pagas": len(parcelas_pagas),
            "parcelas_pendentes": len(parcelas_pendentes),
            "proxima_parcela": parcelas_pendentes[0] if parcelas_pendentes else None,
            "dias_para_vencimento": (endividamento.data_vencimento_final - date.today()).days if endividamento.data_vencimento_final >= date.today() else 0,
            "dias_vencido": (date.today() - endividamento.data_vencimento_final).days if endividamento.data_vencimento_final < date.today() else 0,
        }

        return render_template(
            "admin/endividamentos/visualizar.html",
            endividamento=endividamento,
            date=date,
            proximas_notificacoes=proximas_notificacoes,
            notificacoes_agendadas=notificacoes_agendadas,
            tem_notificacao_config=tem_notificacao_config,
            areas_vinculadas=areas_vinculadas,
            parcelas_pendentes=parcelas_pendentes,
            parcelas_pagas=parcelas_pagas,
            dashboard=dashboard
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao visualizar endividamento {id}: {str(e)}")
        flash(f"Erro ao carregar detalhes do endividamento: {str(e)}", "danger")
        return redirect(url_for("endividamento.listar"))


@endividamento_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@measure_performance()
def editar(id: int):
    """
    Edita um endividamento existente.
    
    Args:
        id: ID do endividamento a ser editado
        
    Returns:
        Formulário de edição ou redirecionamento após sucesso
    """
    try:
        endividamento = Endividamento.query.get_or_404(id)
        form = EndividamentoForm(obj=endividamento)

        if request.method == "POST":
            if form.validate_on_submit():
                try:
                    # Verificar se a data de vencimento mudou para atualizar notificações
                    data_vencimento_anterior = endividamento.data_vencimento_final
                    
                    # Atualizar campos básicos
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

                    # Atualizar pessoas vinculadas
                    pessoas_ids = request.form.getlist("pessoas_ids")
                    if pessoas_ids:
                        pessoas = Pessoa.query.filter(Pessoa.id.in_(pessoas_ids)).all()
                        endividamento.pessoas = pessoas
                    else:
                        endividamento.pessoas = []

                    # Remover vínculos antigos com fazendas
                    EndividamentoFazenda.query.filter_by(endividamento_id=id).delete()

                    # Adicionar novos vínculos (objetos de crédito)
                    objetos_credito = json.loads(request.form.get("objetos_credito") or "[]")
                    for obj in objetos_credito:
                        if obj.get("fazenda_id") and obj.get("hectares"):
                            vinculo = EndividamentoFazenda(
                                endividamento_id=endividamento.id,
                                fazenda_id=int(obj["fazenda_id"]),
                                hectares=float(obj["hectares"]),
                                tipo="objeto_credito",
                                descricao=sanitize_input(obj.get("descricao", "")),
                            )
                            db.session.add(vinculo)

                    # Adicionar novos vínculos (garantias)
                    garantias = json.loads(request.form.get("garantias") or "[]")
                    for gar in garantias:
                        if gar.get("fazenda_id"):
                            vinculo = EndividamentoFazenda(
                                endividamento_id=endividamento.id,
                                fazenda_id=int(gar["fazenda_id"]),
                                hectares=None,
                                tipo="garantia",
                                descricao=sanitize_input(gar.get("descricao", "")),
                            )
                            db.session.add(vinculo)

                    # Remover parcelas antigas
                    Parcela.query.filter_by(endividamento_id=id).delete()

                    # Adicionar novas parcelas
                    parcelas = json.loads(request.form.get("parcelas") or "[]")
                    for parc in parcelas:
                        if parc.get("data_vencimento") and parc.get("valor"):
                            try:
                                data_venc = datetime.strptime(
                                    parc["data_vencimento"], "%Y-%m-%d"
                                ).date()
                                
                                # Verificar se a parcela estava paga
                                pago = parc.get("pago", False)
                                valor_pago = float(parc.get("valor_pago", 0)) if pago else None
                                data_pagamento = datetime.strptime(
                                    parc.get("data_pagamento", ""), "%Y-%m-%d"
                                ).date() if parc.get("data_pagamento") else None
                                
                                parcela = Parcela(
                                    endividamento_id=endividamento.id,
                                    data_vencimento=data_venc,
                                    valor=float(parc["valor"]),
                                    pago=pago,
                                    valor_pago=valor_pago,
                                    data_pagamento=data_pagamento,
                                    observacoes=sanitize_input(parc.get("observacoes", ""))
                                )
                                db.session.add(parcela)
                            except (ValueError, TypeError) as e:
                                current_app.logger.warning(f"Erro ao processar parcela: {str(e)}")

                    # Salvar todas as alterações
                    db.session.commit()
                    
                    # Limpar cache relacionado
                    clear_related_cache("endividamento")
                    
                    # Se a data de vencimento mudou, recriar notificações
                    if data_vencimento_anterior != endividamento.data_vencimento_final:
                        service = notificacao_endividamento_service
                        service._verificar_e_criar_notificacoes(endividamento)
                        flash("Data de vencimento alterada. Notificações foram reconfiguradas.", "info")
                    
                    flash("Endividamento atualizado com sucesso!", "success")
                    return redirect(url_for("endividamento.visualizar", id=id))

                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Erro ao atualizar endividamento {id}: {str(e)}")
                    flash(f"Erro ao atualizar endividamento: {str(e)}", "danger")
            else:
                # Erros de validação do formulário
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f"Erro no campo {getattr(form, field).label.text}: {error}", "danger")

        # Carregar dados para o formulário
        pessoas = Pessoa.query.order_by(Pessoa.nome).all()
        fazendas = Fazenda.query.order_by(Fazenda.nome).all()
        
        # Preparar os dados das pessoas, fazendas e parcelas para o front-end
        pessoas_selecionadas = [p.id for p in endividamento.pessoas]
        objetos_credito = []
        garantias = []
        
        # Preparar objetos de crédito e garantias
        for vinculo in endividamento.fazenda_vinculos:
            if vinculo.tipo == "objeto_credito":
                objetos_credito.append({
                    "id": vinculo.id,
                    "fazenda_id": vinculo.fazenda_id,
                    "fazenda_nome": vinculo.fazenda.nome if vinculo.fazenda else "Desconhecido",
                    "hectares": float(vinculo.hectares) if vinculo.hectares else 0,
                    "descricao": vinculo.descricao
                })
            elif vinculo.tipo == "garantia":
                garantias.append({
                    "id": vinculo.id,
                    "fazenda_id": vinculo.fazenda_id,
                    "fazenda_nome": vinculo.fazenda.nome if vinculo.fazenda else "Desconhecido",
                    "descricao": vinculo.descricao
                })

        return render_template(
            "admin/endividamentos/form.html",
            form=form,
            pessoas=pessoas,
            fazendas=fazendas,
            endividamento=endividamento,
            pessoas_selecionadas=pessoas_selecionadas,
            objetos_credito_json=json.dumps(objetos_credito),
            garantias_json=json.dumps(garantias),
            parcelas_json=json.dumps([
                {
                    "data_vencimento": p.data_vencimento.strftime("%Y-%m-%d"),
                    "valor": float(p.valor),
                    "pago": p.pago,
                    "valor_pago": float(p.valor_pago) if p.valor_pago else None,
                    "data_pagamento": p.data_pagamento.strftime("%Y-%m-%d") if p.data_pagamento else None,
                    "observacoes": p.observacoes
                }
                for p in endividamento.parcelas
            ]),
            data_atual=date.today().isoformat()
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao editar endividamento {id}: {str(e)}")
        flash(f"Erro ao carregar formulário de edição: {str(e)}", "danger")
        return redirect(url_for("endividamento.listar"))


@endividamento_bp.route("/<int:id>/excluir", methods=["POST"])
@measure_performance()
def excluir(id: int):
    """
    Exclui um endividamento.
    
    Args:
        id: ID do endividamento a ser excluído
        
    Returns:
        Redirecionamento para a lista após excluir
    """
    try:
        endividamento = Endividamento.query.get_or_404(id)
        nome_banco = endividamento.banco
        numero_proposta = endividamento.numero_proposta

        # Excluir registros relacionados para evitar erros de FK
        try:
            # Excluir notificações relacionadas primeiro
            NotificacaoEndividamento.query.filter_by(endividamento_id=id).delete()
            HistoricoNotificacao.query.filter_by(endividamento_id=id).delete()
            
            # Vínculos com áreas devem ser excluídos automaticamente pela cascade
            
            # Excluir o endividamento
            db.session.delete(endividamento)
            db.session.commit()
            
            # Limpar cache relacionado
            clear_related_cache("endividamento")
            
            flash(f"Endividamento {nome_banco} - {numero_proposta} excluído com sucesso!", "success")
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir registros relacionados ao endividamento {id}: {str(e)}")
            flash(f"Erro ao excluir registros relacionados: {str(e)}", "danger")
            return redirect(url_for("endividamento.visualizar", id=id))
            
    except Exception as e:
        current_app.logger.error(f"Erro ao excluir endividamento {id}: {str(e)}")
        flash(f"Erro ao excluir endividamento: {str(e)}", "danger")

    return redirect(url_for("endividamento.listar"))


@endividamento_bp.route("/vencimentos")
@cached(timeout=300)  # Cache por 5 minutos
@measure_performance()
def vencimentos():
    """
    Lista parcelas próximas do vencimento e exibe próximas notificações programadas.
    
    Returns:
        Template renderizado com vencimentos
    """
    try:
        hoje = date.today()

        # Parcelas vencidas (sem pagamento)
        parcelas_vencidas = (
            Parcela.query.options(
                joinedload(Parcela.endividamento)
            ).filter(
                Parcela.data_vencimento < hoje, 
                Parcela.pago.is_(False)
            ).order_by(
                Parcela.data_vencimento.asc()
            ).all()
        )

        # Parcelas a vencer nos próximos 30 dias
        data_limite = hoje + timedelta(days=30)
        
        parcelas_a_vencer = (
            Parcela.query.options(
                joinedload(Parcela.endividamento)
            ).filter(
                and_(
                    Parcela.data_vencimento >= hoje,
                    Parcela.data_vencimento <= data_limite,
                    Parcela.pago.is_(False),
                )
            ).order_by(
                Parcela.data_vencimento.asc()
            ).all()
        )

        # Adiciona próximas notificações programadas usando o serviço
        service = notificacao_endividamento_service
        
        # Agrupar por endividamento para evitar múltiplas consultas
        endividamentos_ids = set([p.endividamento_id for p in parcelas_a_vencer])
        notificacoes_por_endividamento = {}
        
        for end_id in endividamentos_ids:
            notificacoes_por_endividamento[end_id] = service.obter_proximas_notificacoes(end_id)
        
        for parcela in parcelas_a_vencer:
            parcela.proximas_notificacoes = notificacoes_por_endividamento.get(parcela.endividamento_id, [])

        # Estatísticas para o dashboard
        total_vencido = sum(p.valor for p in parcelas_vencidas)
        total_a_vencer = sum(p.valor for p in parcelas_a_vencer)
        
        # Agrupar por período para gráfico
        periodos = {
            "Hoje": [],
            "Amanhã": [],
            "Próximos 7 dias": [],
            "Próximos 30 dias": []
        }
        
        amanha = hoje + timedelta(days=1)
        data_7_dias = hoje + timedelta(days=7)
        
        for parcela in parcelas_a_vencer:
            if parcela.data_vencimento == hoje:
                periodos["Hoje"].append(parcela)
            elif parcela.data_vencimento == amanha:
                periodos["Amanhã"].append(parcela)
            elif parcela.data_vencimento <= data_7_dias:
                periodos["Próximos 7 dias"].append(parcela)
            else:
                periodos["Próximos 30 dias"].append(parcela)

        return render_template(
            "admin/endividamentos/vencimentos.html",
            parcelas_vencidas=parcelas_vencidas,
            parcelas_a_vencer=parcelas_a_vencer,
            total_vencido=total_vencido,
            total_a_vencer=total_a_vencer,
            periodos=periodos,
            hoje=hoje,
            date=date
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao listar vencimentos: {str(e)}")
        flash(f"Erro ao carregar vencimentos: {str(e)}", "danger")
        return render_template(
            "admin/endividamentos/vencimentos.html",
            parcelas_vencidas=[],
            parcelas_a_vencer=[],
            date=date
        )


@endividamento_bp.route("/parcela/<int:id>/pagar", methods=["POST"])
@measure_performance()
def pagar_parcela(id: int):
    """
    Marca uma parcela como paga.
    
    Args:
        id: ID da parcela
        
    Returns:
        Redirecionamento para a tela de vencimentos
    """
    try:
        parcela = Parcela.query.get_or_404(id)
        endividamento_id = parcela.endividamento_id

        # Registrar o pagamento
        parcela.pago = True
        parcela.data_pagamento = datetime.strptime(
            request.form.get("data_pagamento", date.today().isoformat()),
            "%Y-%m-%d"
        ).date()
        
        parcela.valor_pago = float(request.form.get("valor_pago", parcela.valor))
        parcela.observacoes = sanitize_input(request.form.get("observacoes", ""))

        db.session.commit()
        
        # Limpar cache relacionado
        clear_related_cache("endividamento")
        
        flash(f"Parcela no valor de R$ {parcela.valor:,.2f} marcada como paga!", "success")
        
        # Redirecionar para o endividamento ou vencimentos
        if request.form.get("redirect_to") == "endividamento":
            return redirect(url_for("endividamento.visualizar", id=endividamento_id))
        else:
            return redirect(url_for("endividamento.vencimentos"))
            
    except ValueError as e:
        db.session.rollback()
        flash(f"Valor inválido: {str(e)}", "danger")
        return redirect(url_for("endividamento.vencimentos"))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao marcar parcela {id} como paga: {str(e)}")
        flash(f"Erro ao marcar parcela como paga: {str(e)}", "danger")
        return redirect(url_for("endividamento.vencimentos"))


@endividamento_bp.route("/api/fazendas/<int:pessoa_id>")
@cached(timeout=600, key_prefix="fazendas_pessoa")
def api_fazendas_pessoa(pessoa_id: int):
    """
    API para obter fazendas de uma pessoa.
    
    Args:
        pessoa_id: ID da pessoa
        
    Returns:
        Lista de fazendas em formato JSON
    """
    try:
        pessoa = Pessoa.query.get_or_404(pessoa_id)
        fazendas = [
            {
                "id": f.id, 
                "nome": f.nome, 
                "tamanho_total": float(f.tamanho_total),
                "municipio": f.municipio,
                "matricula": f.matricula
            }
            for f in pessoa.fazendas
        ]
        return jsonify(fazendas)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar fazendas da pessoa {pessoa_id}: {str(e)}")
        return jsonify({"erro": str(e)}), 500


@endividamento_bp.route("/buscar-pessoas")
@cached(timeout=300, key_prefix="buscar_pessoas")
@measure_performance()
def buscar_pessoas():
    """
    Endpoint para busca AJAX de pessoas com cache Redis e paginação.
    
    Returns:
        Lista de pessoas filtradas em formato JSON
    """
    try:
        from src.utils.cache import cache

        termo = request.args.get("q", "").strip()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)

        if len(termo) < 2:
            return jsonify([])

        # Validar e sanitizar parâmetros
        page = max(1, page)
        limit = min(max(1, limit), 50)

        # Chave de cache específica para esta consulta
        cache_key = f"buscar_pessoas:{termo.lower()}:{page}:{limit}"

        # Verificar cache
        resultado_cache = cache.get(cache_key)
        if resultado_cache is not None:
            return jsonify(resultado_cache)

        # Calcular offset para paginação
        offset = (page - 1) * limit

        # Construir consulta com índices apropriados
        query = Pessoa.query.filter(
            or_(
                Pessoa.nome.ilike(f"%{termo}%"), 
                Pessoa.cpf_cnpj.ilike(f"%{termo}%")
            )
        )

        # Contar total para paginação
        total_count = query.count()
        
        # Executar consulta com limite
        pessoas = query.order_by(Pessoa.nome).offset(offset).limit(limit).all()

        # Transformar resultados
        resultado = []
        for pessoa in pessoas:
            fazendas_count = len(pessoa.fazendas) if hasattr(pessoa, 'fazendas') else 0
            
            resultado.append({
                "id": pessoa.id,
                "nome": pessoa.nome,
                "cpf_cnpj": pessoa.cpf_cnpj,
                "cpf_cnpj_formatado": pessoa.formatar_cpf_cnpj() if hasattr(pessoa, 'formatar_cpf_cnpj') else pessoa.cpf_cnpj,
                "fazendas_count": fazendas_count
            })

        # Preparar resposta com paginação se solicitado
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
        else:
            response_data = resultado

        # Armazenar em cache (5 minutos)
        cache.set(cache_key, response_data, timeout=300)

        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar pessoas: {str(e)}")
        return jsonify({"erro": str(e)}), 500


@endividamento_bp.route("/<int:id>/notificacoes", methods=["GET", "POST"])
@measure_performance()
def configurar_notificacoes(id: int):
    """
    Configura notificações para um endividamento.
    
    Args:
        id: ID do endividamento
        
    Returns:
        Template para configuração de notificações
    """
    try:
        endividamento = Endividamento.query.get_or_404(id)
        form = NotificacaoEndividamentoForm()
        service = notificacao_endividamento_service
        
        # Obter informações atuais
        hoje = date.today()
        
        # Buscar notificações já agendadas
        notificacoes_agendadas = NotificacaoEndividamento.query.filter_by(
            endividamento_id=id,
            ativo=True
        ).order_by(NotificacaoEndividamento.data_envio).all()
        
        # Separar notificações por status
        notif_pendentes = []
        notif_enviadas = []
        notif_falhas = []
        
        for notif in notificacoes_agendadas:
            if notif.tipo_notificacao != 'config':  # Ignorar configuração
                if notif.enviado:
                    notif_enviadas.append(notif)
                elif notif.tentativas >= 3:
                    notif_falhas.append(notif)
                else:
                    notif_pendentes.append(notif)
        
        # Calcular próximas notificações
        proximas_notificacoes = service.obter_proximas_notificacoes(id)

        # Processar o formulário ao enviar
        if request.method == "POST":
            if form.validate_on_submit():
                try:
                    # Obter lista de emails
                    emails = form.get_emails_list()
                    
                    # Obter prazos selecionados (se implementado no form)
                    prazos = form.prazos.data if hasattr(form, 'prazos') else None

                    # Configurar notificações
                    sucesso = service.configurar_notificacao(
                        endividamento_id=id, 
                        emails=emails, 
                        ativo=form.ativo.data
                    )

                    if sucesso:
                        # Limpar cache relacionado
                        clear_related_cache("endividamento")
                        clear_related_cache("notificacao")
                        
                        flash("Configurações de notificação salvas com sucesso!", "success")
                        return redirect(url_for("endividamento.visualizar", id=id))
                    else:
                        flash("Erro ao salvar configurações de notificação.", "danger")

                except Exception as e:
                    current_app.logger.error(f"Erro ao configurar notificações: {str(e)}")
                    flash(f"Erro ao processar configurações: {str(e)}", "danger")
            else:
                # Mostrar erros de validação
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f"{getattr(form, field).label.text}: {error}", "danger")

        # Carregar configuração existente para o formulário
        configuracao = service.obter_configuracao(id)
        if configuracao["emails"]:
            form.set_emails_from_list(configuracao["emails"])
            form.ativo.data = configuracao["ativo"]
        else:
            # Sugerir emails das pessoas vinculadas
            emails_sugeridos = []
            for pessoa in endividamento.pessoas:
                if hasattr(pessoa, 'email') and pessoa.email:
                    emails_sugeridos.append(pessoa.email)
            if emails_sugeridos:
                form.set_emails_from_list(emails_sugeridos)

        # Obter histórico de notificações
        historico = service.obter_historico(id)
        
        # Estatísticas para dashboard
        stats = {
            'total_agendadas': len(notif_pendentes),
            'total_enviadas': len(notif_enviadas),
            'total_falhas': len(notif_falhas),
            'proxima_notificacao': proximas_notificacoes[0] if proximas_notificacoes else None,
            'dias_para_vencimento': (endividamento.data_vencimento_final - hoje).days if endividamento.data_vencimento_final >= hoje else 0,
            'dias_desde_configuracao': (hoje - configuracao.get('data_configuracao', hoje)).days if 'data_configuracao' in configuracao else 0
        }

        return render_template(
            "admin/endividamentos/notificacoes.html",
            endividamento=endividamento,
            form=form,
            historico=historico,
            proximas_notificacoes=proximas_notificacoes,
            notificacoes_pendentes=notif_pendentes,
            notificacoes_enviadas=notif_enviadas,
            notificacoes_falhas=notif_falhas,
            stats=stats,
            hoje=hoje
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar configuração de notificações para endividamento {id}: {str(e)}")
        flash(f"Erro ao carregar configurações de notificação: {str(e)}", "danger")
        return redirect(url_for("endividamento.visualizar", id=id))


@endividamento_bp.route("/<int:id>/notificacoes/status")
@cached(timeout=60)  # Cache por 1 minuto
def status_notificacoes(id: int):
    """
    API para obter status das notificações de um endividamento.
    
    Args:
        id: ID do endividamento
        
    Returns:
        JSON com status das notificações
    """
    try:
        endividamento = Endividamento.query.get_or_404(id)
        
        # Buscar todas as notificações
        notificacoes = NotificacaoEndividamento.query.filter_by(
            endividamento_id=id
        ).order_by(NotificacaoEndividamento.data_envio).all()
        
        pendentes = []
        enviadas = []
        falhas = []
        
        for notif in notificacoes:
            if notif.ativo and notif.tipo_notificacao != 'config':
                dados = {
                    'id': notif.id,
                    'tipo': notif.tipo_notificacao,
                    'data_envio': notif.data_envio.isoformat() if notif.data_envio else None,
                    'tentativas': notif.tentativas,
                    'emails': json.loads(notif.emails) if notif.emails else []
                }
                
                if notif.enviado:
                    dados['data_envio_realizado'] = notif.data_envio_realizado.isoformat() if notif.data_envio_realizado else None
                    enviadas.append(dados)
                elif notif.tentativas >= 3:
                    dados['erro'] = notif.erro_mensagem
                    falhas.append(dados)
                else:
                    # Calcular tempo restante/atraso
                    agora = datetime.utcnow()
                    if notif.data_envio > agora:
                        delta = notif.data_envio - agora
                        dados['tempo_restante'] = {
                            'dias': delta.days,
                            'horas': delta.seconds // 3600,
                            'minutos': (delta.seconds % 3600) // 60
                        }
                    else:
                        delta = agora - notif.data_envio
                        dados['atraso'] = {
                            'dias': delta.days,
                            'horas': delta.seconds // 3600,
                            'minutos': (delta.seconds % 3600) // 60
                        }
                    pendentes.append(dados)
        
        # Obter configuração
        configuracao = notificacao_endividamento_service.obter_configuracao(id)
        
        return jsonify({
            'endividamento_id': id,
            'banco': endividamento.banco,
            'vencimento': endividamento.data_vencimento_final.isoformat(),
            'configuracao': {
                'ativa': configuracao.get('ativo', False),
                'emails': configuracao.get('emails', []),
                'ultima_atualizacao': configuracao.get('ultima_atualizacao', None)
            },
            'notificacoes': {
                'pendentes': pendentes,
                'enviadas': enviadas,
                'falhas': falhas,
                'total': len(notificacoes) - 1 if any(n.tipo_notificacao == 'config' for n in notificacoes) else len(notificacoes)
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter status das notificações do endividamento {id}: {str(e)}")
        return jsonify({"erro": str(e)}), 500


@endividamento_bp.route("/<int:id>/notificacoes/reenviar/<int:notif_id>", methods=["POST"])
@measure_performance()
def reenviar_notificacao(id: int, notif_id: int):
    """
    Força o reenvio de uma notificação específica.
    
    Args:
        id: ID do endividamento
        notif_id: ID da notificação
        
    Returns:
        JSON com resultado do reenvio
    """
    try:
        # Validar permissões e existência
        notificacao = NotificacaoEndividamento.query.filter_by(
            id=notif_id,
            endividamento_id=id
        ).first_or_404()
        
        if notificacao.enviado:
            return jsonify({
                'sucesso': False,
                'erro': 'Esta notificação já foi enviada'
            }), 400
        
        if notificacao.tentativas >= 3:
            # Reset tentativas para permitir reenvio
            notificacao.tentativas = 0
            notificacao.erro_mensagem = None
            db.session.commit()
        
        # Forçar processamento imediato
        service = notificacao_endividamento_service
        
        sucesso = service._enviar_notificacao_agendada(notificacao)
        
        # Atualizar dados após envio
        db.session.refresh(notificacao)
        
        return jsonify({
            'sucesso': sucesso,
            'mensagem': 'Notificação reenviada com sucesso' if sucesso else 'Falha no reenvio',
            'tentativas': notificacao.tentativas,
            'enviado': notificacao.enviado,
            'data_envio': notificacao.data_envio_realizado.isoformat() if notificacao.data_envio_realizado else None,
            'erro': notificacao.erro_mensagem
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao reenviar notificação {notif_id} do endividamento {id}: {str(e)}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@endividamento_bp.route("/notificacoes/dashboard")
@measure_performance()
def dashboard_notificacoes():
    """
    Dashboard geral de notificações de endividamentos.
    
    Returns:
        Template com dashboard de notificações
    """
    try:
        # Estatísticas gerais
        total_endividamentos = Endividamento.query.count()
        endividamentos_ativos = Endividamento.query.filter(
            Endividamento.data_vencimento_final > date.today()
        ).count()
        
        # Notificações
        total_notificacoes = NotificacaoEndividamento.query.filter(
            NotificacaoEndividamento.tipo_notificacao != 'config'
        ).count()
        
        notificacoes_pendentes = NotificacaoEndividamento.query.filter(
            NotificacaoEndividamento.ativo == True,
            NotificacaoEndividamento.enviado == False,
            NotificacaoEndividamento.tipo_notificacao != 'config',
            NotificacaoEndividamento.data_envio <= datetime.utcnow()
        ).count()
        
        notificacoes_futuras = NotificacaoEndividamento.query.filter(
            NotificacaoEndividamento.ativo == True,
            NotificacaoEndividamento.enviado == False,
            NotificacaoEndividamento.tipo_notificacao != 'config',
            NotificacaoEndividamento.data_envio > datetime.utcnow()
        ).count()
        
        notificacoes_enviadas = NotificacaoEndividamento.query.filter(
            NotificacaoEndividamento.enviado == True,
            NotificacaoEndividamento.tipo_notificacao != 'config'
        ).count()
        
        notificacoes_falhas = NotificacaoEndividamento.query.filter(
            NotificacaoEndividamento.ativo == True,
            NotificacaoEndividamento.enviado == False,
            NotificacaoEndividamento.tentativas >= 3,
            NotificacaoEndividamento.tipo_notificacao != 'config'
        ).count()
        
        # Próximas 10 notificações
        proximas = NotificacaoEndividamento.query.options(
            joinedload(NotificacaoEndividamento.endividamento)
        ).filter(
            NotificacaoEndividamento.ativo == True,
            NotificacaoEndividamento.enviado == False,
            NotificacaoEndividamento.tipo_notificacao != 'config'
        ).order_by(NotificacaoEndividamento.data_envio).limit(10).all()
        
        # Últimas 10 enviadas
        ultimas_enviadas = NotificacaoEndividamento.query.options(
            joinedload(NotificacaoEndividamento.endividamento)
        ).filter(
            NotificacaoEndividamento.enviado == True,
            NotificacaoEndividamento.tipo_notificacao != 'config'
        ).order_by(NotificacaoEndividamento.data_envio_realizado.desc()).limit(10).all()
        
        # Endividamentos sem notificação configurada
        endividamentos_sem_notif = db.session.query(Endividamento).outerjoin(
            NotificacaoEndividamento,
            and_(
                NotificacaoEndividamento.endividamento_id == Endividamento.id,
                NotificacaoEndividamento.tipo_notificacao == 'config',
                NotificacaoEndividamento.ativo == True
            )
        ).filter(
            NotificacaoEndividamento.id.is_(None),
            Endividamento.data_vencimento_final > date.today()
        ).limit(10).all()
        
        # Lista de endividamentos sem notificação para exibir
        endividamentos_sem_notif_lista = [
            {
                'id': e.id,
                'banco': e.banco,
                'numero_proposta': e.numero_proposta,
                'vencimento': e.data_vencimento_final,
                'dias_para_vencimento': (e.data_vencimento_final - date.today()).days
            }
            for e in endividamentos_sem_notif
        ]
        
        # Histórico recente de notificações
        historico_recente = HistoricoNotificacao.query.options(
            joinedload(HistoricoNotificacao.endividamento)
        ).order_by(
            HistoricoNotificacao.data_envio.desc()
        ).limit(10).all()
        
        return render_template(
            "admin/endividamentos/dashboard_notificacoes.html",
            stats={
                'total_endividamentos': total_endividamentos,
                'endividamentos_ativos': endividamentos_ativos,
                'endividamentos_sem_notif': len(endividamentos_sem_notif_lista),
                'total_notificacoes': total_notificacoes,
                'notificacoes_pendentes': notificacoes_pendentes,
                'notificacoes_futuras': notificacoes_futuras,
                'notificacoes_enviadas': notificacoes_enviadas,
                'notificacoes_falhas': notificacoes_falhas
            },
            proximas_notificacoes=proximas,
            ultimas_enviadas=ultimas_enviadas,
            endividamentos_sem_notif=endividamentos_sem_notif_lista,
            historico_recente=historico_recente,
            hoje=date.today()
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar dashboard de notificações: {str(e)}")
        flash(f"Erro ao carregar dashboard: {str(e)}", "danger")
        return render_template(
            "admin/endividamentos/dashboard_notificacoes.html",
            stats={},
            proximas_notificacoes=[],
            ultimas_enviadas=[],
            hoje=date.today(),
            erro=str(e)
        )


@endividamento_bp.route("/api/processar-notificacoes", methods=["POST"])
@measure_performance()
def processar_notificacoes():
    """
    API para processar notificações manualmente (para testes).
    
    Returns:
        JSON com resultado do processamento
    """
    try:
        service = notificacao_endividamento_service
        start_time = datetime.now()
        
        notificacoes_enviadas = service.verificar_e_enviar_notificacoes()
        
        duration = (datetime.now() - start_time).total_seconds()

        return jsonify(
            {
                "sucesso": True,
                "notificacoes_enviadas": notificacoes_enviadas,
                "mensagem": f"{notificacoes_enviadas} notificações foram enviadas em {duration:.2f}s.",
                "duracao_segundos": round(duration, 2),
                "timestamp": datetime.now().isoformat()
            }
        )

    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500
