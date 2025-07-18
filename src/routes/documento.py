# /src/routes/documento.py

"""
Rotas para gerenciamento de documentos.
Inclui APIs REST e views para administração de documentos,
upload de arquivos, notificações e monitoramento de vencimentos.
"""

import os
import datetime
import traceback
from typing import Dict, Any, List, Optional, Tuple, Union

from flask import Blueprint, current_app, jsonify, request, render_template, flash, redirect, url_for, send_file, abort
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, and_, or_
from werkzeug.utils import secure_filename

from src.models.db import db
from src.models.documento import Documento, TipoDocumento, StatusProcessamento
from src.models.fazenda import Fazenda
from src.models.pessoa import Pessoa
from src.models.usuario import Usuario
from src.models.notificacao_documento import HistoricoNotificacaoDocumento
from src.utils.email_service import email_service
from src.utils.notificacao_utils import calcular_proximas_notificacoes_programadas
from src.utils.tasks import process_document_upload
from src.utils.cache import cached
from src.utils.performance import measure_performance, clear_related_cache
from src.utils.notificacoes import verificar_documentos_vencimento, gerar_alertas_vencimento

# Blueprints
documento_bp = Blueprint("documento", __name__, url_prefix="/api/documentos")
admin_documentos_bp = Blueprint("admin_documentos", __name__, url_prefix="/admin/documentos")


def data_valida(data_str):
    """Valida e converte string de data para objeto date."""
    try:
        return datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def arquivo_permitido(filename: str) -> bool:
    """
    Verifica se a extensão do arquivo é permitida
    
    Args:
        filename: Nome do arquivo a verificar
    
    Returns:
        True se a extensão for permitida
    """
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# -------- API ROUTES --------

@documento_bp.route("/", methods=["GET"])
@measure_performance()
def listar_documentos():
    """
    Lista todos os documentos cadastrados.
    
    Suporta filtragem por tipo, vencimento e status.
    
    Returns:
        JSON com lista de documentos
    """
    try:
        # Parâmetros de filtragem
        tipo = request.args.get('tipo')
        vencidos = request.args.get('vencidos', 'false').lower() == 'true'
        proximos = request.args.get('proximos', 'false').lower() == 'true'
        ativos = request.args.get('ativos', 'true').lower() == 'true'
        
        # Construir consulta com filtros
        query = Documento.query
        
        if ativos:
            query = query.filter(Documento.ativo == True)
        
        if tipo:
            try:
                tipo_enum = TipoDocumento(tipo)
                query = query.filter(Documento.tipo == tipo_enum)
            except ValueError:
                pass
        
        hoje = datetime.date.today()
        
        if vencidos:
            query = query.filter(
                Documento.data_vencimento.isnot(None),
                Documento.data_vencimento < hoje
            )
        elif proximos:
            # Próximos 30 dias
            data_limite = hoje + datetime.timedelta(days=30)
            query = query.filter(
                Documento.data_vencimento.isnot(None),
                Documento.data_vencimento >= hoje,
                Documento.data_vencimento <= data_limite
            )
            
        # Ordenar por vencimento (mais próximos primeiro)
        query = query.order_by(Documento.data_vencimento.asc())
        
        documentos = query.all()
        resultado = []
        
        for documento in documentos:
            fazenda_nome = documento.fazenda.nome if documento.fazenda else None
            fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
            pessoa_nome = documento.pessoa.nome if documento.pessoa else None
            responsavel_nome = documento.responsavel.nome if documento.responsavel else None

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
                    "responsavel_id": documento.responsavel_id,
                    "responsavel_nome": responsavel_nome,
                    "emails_notificacao": documento.emails_notificacao,
                    "prazos_notificacao": documento.prazos_notificacao,
                    "esta_vencido": documento.esta_vencido,
                    "proximo_vencimento": documento.proximo_vencimento,
                    "status_processamento": documento.status_processamento.value if hasattr(documento, 'status_processamento') else None,
                    "tem_arquivo": bool(documento.caminho_arquivo),
                    "ativo": documento.ativo if hasattr(documento, 'ativo') else True,
                    "tamanho_arquivo": documento.tamanho_arquivo_formatado if hasattr(documento, 'tamanho_arquivo_formatado') else None,
                }
            )
        return jsonify(resultado)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar documentos: {str(e)}")
        return jsonify({"erro": "Erro ao listar documentos", "detalhes": str(e)}), 500


@documento_bp.route("/<int:id>", methods=["GET"])
@measure_performance()
def obter_documento(id: int):
    """
    Obtém detalhes de um documento específico.
    
    Args:
        id: ID do documento
        
    Returns:
        JSON com detalhes do documento
    """
    try:
        documento = Documento.query.get_or_404(id)

        fazenda_nome = documento.fazenda.nome if documento.fazenda else None
        fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
        pessoa_nome = documento.pessoa.nome if documento.pessoa else None
        responsavel_nome = documento.responsavel.nome if documento.responsavel else None

        # Calcular próximas notificações
        prazos = documento.prazos_notificacao if documento.prazos_notificacao else [30, 15, 7, 1]
        prazos = [int(p) for p in prazos]
        
        # Obter histórico real de notificações enviadas
        enviados = []
        try:
            historico = HistoricoNotificacaoDocumento.query.filter_by(documento_id=id).all()
            for h in historico:
                enviados.append({
                    "dias_restantes": h.dias_restantes,
                    "data_envio": h.data_envio.isoformat() if h.data_envio else None,
                    "sucesso": h.sucesso,
                    "destinatarios": h.destinatarios_lista
                })
        except Exception as e:
            current_app.logger.warning(f"Erro ao obter histórico de notificações: {str(e)}")
            
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
                "responsavel_id": documento.responsavel_id,
                "responsavel_nome": responsavel_nome,
                "emails_notificacao": documento.emails_notificacao,
                "prazos_notificacao": documento.prazos_notificacao,
                "esta_vencido": documento.esta_vencido,
                "proximo_vencimento": documento.proximo_vencimento,
                "proximas_notificacoes": proximas_notificacoes,
                "historico_notificacoes": enviados,
                "status_processamento": documento.status_processamento.value if hasattr(documento, 'status_processamento') else None,
                "tem_arquivo": bool(documento.caminho_arquivo),
                "data_processamento": documento.data_processamento.isoformat() if hasattr(documento, 'data_processamento') and documento.data_processamento else None,
                "erro_processamento": documento.erro_processamento if hasattr(documento, 'erro_processamento') else None,
                "ativo": documento.ativo if hasattr(documento, 'ativo') else True,
                "tamanho_arquivo": documento.tamanho_arquivo_formatado if hasattr(documento, 'tamanho_arquivo_formatado') else None,
                "extensao_arquivo": documento.extensao_arquivo if hasattr(documento, 'extensao_arquivo') else None,
                "ultima_notificacao": documento.ultima_notificacao.isoformat() if hasattr(documento, 'ultima_notificacao') and documento.ultima_notificacao else None,
                "data_criacao": documento.data_criacao.isoformat() if documento.data_criacao else None,
                "data_atualizacao": documento.data_atualizacao.isoformat() if documento.data_atualizacao else None,
            }
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao obter documento {id}: {str(e)}")
        return (
            jsonify({"erro": f"Erro ao obter documento {id}", "detalhes": str(e)}),
            500,
        )


@documento_bp.route("/", methods=["POST"])
@measure_performance()
def criar_documento():
    """
    Cria um novo documento.
    
    Suporta JSON ou form-data com arquivo anexado.
    
    Returns:
        JSON com o documento criado e status 201
    """
    try:
        # Determinar se o request tem form-data ou JSON
        arquivo = None
        if request.files and 'arquivo' in request.files:
            arquivo = request.files['arquivo']
            dados = request.form
        else:
            dados = request.json or {}
            
        # Validar campos obrigatórios
        campos_obrigatorios = ["nome", "tipo", "data_emissao"]
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({"erro": f"Campo {campo} é obrigatório"}), 400

        # Validar tipo de documento
        try:
            tipo_documento = TipoDocumento(dados.get("tipo"))
        except ValueError:
            return jsonify({"erro": "Tipo de documento inválido"}), 400

        # Validar data de emissão
        data_emissao = data_valida(dados.get("data_emissao"))
        if not data_emissao:
            return (
                jsonify({"erro": "Data de emissão inválida. Use o formato YYYY-MM-DD"}), 400
            )

        # Validar data de vencimento
        data_vencimento = None
        if dados.get("data_vencimento"):
            data_vencimento = data_valida(dados.get("data_vencimento"))
            if not data_vencimento:
                return (
                    jsonify({"erro": "Data de vencimento inválida. Use o formato YYYY-MM-DD"}), 400
                )

        # Validar fazenda_id
        fazenda_id = int(dados.get("fazenda_id")) if dados.get("fazenda_id") else None
        if fazenda_id:
            fazenda = Fazenda.query.get(fazenda_id)
            if not fazenda:
                return jsonify({"erro": "Fazenda não encontrada"}), 404
        else:
            fazenda = None
            
        # Validar pessoa_id
        pessoa_id = int(dados.get("pessoa_id")) if dados.get("pessoa_id") else None
        if pessoa_id:
            pessoa = Pessoa.query.get(pessoa_id)
            if not pessoa:
                return jsonify({"erro": "Pessoa não encontrada"}), 404
        else:
            pessoa = None
            
        # Validar responsavel_id
        responsavel_id = int(dados.get("responsavel_id")) if dados.get("responsavel_id") else None
        if responsavel_id:
            responsavel = Usuario.query.get(responsavel_id)
            if not responsavel:
                return jsonify({"erro": "Usuário responsável não encontrado"}), 404
        else:
            responsavel = None

        # Processar prazos de notificação
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

        # Criar o novo documento
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
            pessoa_id=pessoa_id,
            responsavel_id=responsavel_id,
            ativo=True,
            status_processamento=StatusProcessamento.NAO_PROCESSADO
        )

        # Configurar notificações
        novo_documento.emails_notificacao = dados.get("emails_notificacao", "")
        novo_documento.prazos_notificacao = prazos_notificacao

        # Processar arquivo anexado
        if arquivo and arquivo.filename:
            if not arquivo_permitido(arquivo.filename):
                return jsonify({"erro": "Tipo de arquivo não permitido"}), 400

            try:
                # Salvar arquivo
                filename = secure_filename(arquivo.filename)
                upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                
                # Garantir que o diretório existe
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                    
                # Criar estrutura de pastas com base na data
                today = datetime.date.today()
                year_month = today.strftime('%Y/%m')
                target_dir = os.path.join(upload_dir, year_month)
                
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                
                # Gerar nome único para o arquivo
                base, ext = os.path.splitext(filename)
                unique_filename = f"{base}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                file_path = os.path.join(target_dir, unique_filename)
                
                arquivo.save(file_path)
                
                # Atualizar documento com informações do arquivo
                novo_documento.caminho_arquivo = file_path
                novo_documento.tamanho_arquivo = os.path.getsize(file_path)
                novo_documento.status_processamento = StatusProcessamento.EM_PROCESSAMENTO
                
            except Exception as e:
                current_app.logger.error(f"Erro ao salvar arquivo: {str(e)}")
                return jsonify({"erro": "Erro ao processar arquivo", "detalhes": str(e)}), 500

        # Salvar documento no banco de dados
        db.session.add(novo_documento)
        db.session.commit()
        
        # Agendar processamento do arquivo em background se necessário
        if arquivo and arquivo.filename and hasattr(novo_documento, 'caminho_arquivo'):
            try:
                # Usar Celery para processamento assíncrono
                process_document_upload.delay(
                    document_id=novo_documento.id,
                    file_path=novo_documento.caminho_arquivo
                )
            except Exception as e:
                current_app.logger.error(f"Erro ao agendar processamento do arquivo: {str(e)}")
        
        # Limpar cache relacionado
        clear_related_cache("documento")

        # Preparar resposta
        fazenda_nome = fazenda.nome if fazenda else None
        fazenda_matricula = fazenda.matricula if fazenda else None
        pessoa_nome = pessoa.nome if pessoa else None
        responsavel_nome = responsavel.nome if responsavel else None

        return (
            jsonify(
                {
                    "id": novo_documento.id,
                    "nome": novo_documento.nome,
                    "tipo": novo_documento.tipo.value,
                    "tipo_personalizado": novo_documento.tipo_personalizado,
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
                    "responsavel_id": novo_documento.responsavel_id,
                    "responsavel_nome": responsavel_nome,
                    "emails_notificacao": novo_documento.emails_notificacao,
                    "prazos_notificacao": novo_documento.prazos_notificacao,
                    "tem_arquivo": bool(getattr(novo_documento, 'caminho_arquivo', None)),
                    "status_processamento": novo_documento.status_processamento.value if hasattr(novo_documento, 'status_processamento') else None,
                    "mensagem": "Documento criado com sucesso"
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
@measure_performance()
def atualizar_documento(id: int):
    """
    Atualiza os dados de um documento existente.
    
    Args:
        id: ID do documento a ser atualizado
        
    Returns:
        JSON com o documento atualizado
    """
    try:
        documento = Documento.query.get_or_404(id)
        
        # Determinar se o request tem form-data ou JSON
        arquivo = None
        if request.files and 'arquivo' in request.files:
            arquivo = request.files['arquivo']
            dados = request.form
        else:
            dados = request.json or {}

        if not dados and not arquivo:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        # Atualizar os campos do documento
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

        # Atualizar os relacionamentos
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
                
        if "responsavel_id" in dados:
            responsavel_id = int(dados.get("responsavel_id")) if dados.get("responsavel_id") else None
            if responsavel_id:
                responsavel = Usuario.query.get(responsavel_id)
                if not responsavel:
                    return jsonify({"erro": "Usuário responsável não encontrado"}), 404
                documento.responsavel_id = responsavel_id
            else:
                documento.responsavel_id = None

        if "emails_notificacao" in dados:
            documento.emails_notificacao = dados.get("emails_notificacao", "")
            
        if "ativo" in dados:
            documento.ativo = dados.get("ativo") in (True, 'true', '1', 1)

        # Atualizar prazos de notificação
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

        # Processar arquivo anexado, se houver
        if arquivo and arquivo.filename:
            if not arquivo_permitido(arquivo.filename):
                return jsonify({"erro": "Tipo de arquivo não permitido"}), 400

            try:
                # Salvar arquivo
                filename = secure_filename(arquivo.filename)
                upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                
                # Garantir que o diretório existe
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                    
                # Criar estrutura de pastas com base na data
                today = datetime.date.today()
                year_month = today.strftime('%Y/%m')
                target_dir = os.path.join(upload_dir, year_month)
                
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                
                # Gerar nome único para o arquivo
                base, ext = os.path.splitext(filename)
                unique_filename = f"{base}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                file_path = os.path.join(target_dir, unique_filename)
                
                # Excluir arquivo anterior se existir
                if hasattr(documento, 'caminho_arquivo') and documento.caminho_arquivo:
                    try:
                        if os.path.exists(documento.caminho_arquivo):
                            os.remove(documento.caminho_arquivo)
                    except Exception as e:
                        current_app.logger.warning(f"Erro ao remover arquivo antigo: {str(e)}")
                
                arquivo.save(file_path)
                
                # Atualizar documento com informações do arquivo
                documento.caminho_arquivo = file_path
                documento.tamanho_arquivo = os.path.getsize(file_path)
                documento.status_processamento = StatusProcessamento.EM_PROCESSAMENTO
                
                # Agendar processamento do arquivo em background
                process_document_upload.delay(
                    document_id=documento.id,
                    file_path=file_path
                )
                
            except Exception as e:
                current_app.logger.error(f"Erro ao salvar arquivo: {str(e)}")
                return jsonify({"erro": "Erro ao processar arquivo", "detalhes": str(e)}), 500

        # Salvar alterações
        db.session.commit()
        
        # Limpar cache relacionado
        clear_related_cache("documento")

        # Preparar resposta
        fazenda_nome = documento.fazenda.nome if documento.fazenda else None
        fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
        pessoa_nome = documento.pessoa.nome if documento.pessoa else None
        responsavel_nome = documento.responsavel.nome if documento.responsavel else None

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
                "responsavel_id": documento.responsavel_id,
                "responsavel_nome": responsavel_nome,
                "emails_notificacao": documento.emails_notificacao,
                "prazos_notificacao": documento.prazos_notificacao,
                "tem_arquivo": bool(getattr(documento, 'caminho_arquivo', None)),
                "status_processamento": documento.status_processamento.value if hasattr(documento, 'status_processamento') else None,
                "ativo": documento.ativo if hasattr(documento, 'ativo') else True,
                "mensagem": "Documento atualizado com sucesso"
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
@measure_performance()
def excluir_documento(id: int):
    """
    Exclui um documento do sistema.
    
    Args:
        id: ID do documento a ser excluído
        
    Returns:
        JSON com mensagem de confirmação
    """
    try:
        documento = Documento.query.get_or_404(id)
        nome = documento.nome
        
        # Se tiver arquivo associado, excluir do sistema
        if hasattr(documento, 'caminho_arquivo') and documento.caminho_arquivo:
            try:
                if os.path.exists(documento.caminho_arquivo):
                    os.remove(documento.caminho_arquivo)
            except Exception as e:
                current_app.logger.warning(f"Erro ao remover arquivo: {str(e)}")
        
        # Remover histórico de notificações
        try:
            historico = HistoricoNotificacaoDocumento.query.filter_by(documento_id=id).all()
            for h in historico:
                db.session.delete(h)
        except Exception as e:
            current_app.logger.warning(f"Erro ao remover histórico de notificações: {str(e)}")

        # Excluir o documento
        db.session.delete(documento)
        db.session.commit()
        
        # Limpar cache relacionado
        clear_related_cache("documento")

        return jsonify({
            "mensagem": f"Documento {nome} excluído com sucesso",
            "id": id
        }), 200
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


@documento_bp.route("/<int:id>/arquivo", methods=["GET"])
def download_arquivo(id: int):
    """
    Faz o download do arquivo associado a um documento.
    
    Args:
        id: ID do documento
        
    Returns:
        Arquivo para download
    """
    try:
        documento = Documento.query.get_or_404(id)
        
        if not hasattr(documento, 'caminho_arquivo') or not documento.caminho_arquivo:
            return jsonify({"erro": "Documento não possui arquivo"}), 404
            
        if not os.path.exists(documento.caminho_arquivo):
            return jsonify({"erro": "Arquivo não encontrado no servidor"}), 404
            
        # Obter nome original do arquivo
        nome_arquivo = os.path.basename(documento.caminho_arquivo)
        
        # Detectar o tipo MIME com base na extensão
        _, ext = os.path.splitext(documento.caminho_arquivo)
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
        }
        
        mime_type = mime_types.get(ext.lower(), 'application/octet-stream')
        
        return send_file(
            documento.caminho_arquivo,
            mimetype=mime_type,
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao fazer download do arquivo: {str(e)}")
        return jsonify({"erro": "Erro ao fazer download do arquivo", "detalhes": str(e)}), 500


@documento_bp.route("/vencidos", methods=["GET"])
@cached(timeout=300)  # Cache por 5 minutos
@measure_performance()
def listar_documentos_vencidos():
    """
    API: Lista todos os documentos vencidos ou próximos do vencimento.
    
    Returns:
        JSON com documentos vencidos e próximos do vencimento
    """
    try:
        # Usar a função utilitária para verificar documentos
        documentos_vencidos, documentos_proximos = verificar_documentos_vencimento()
        
        # Converter para formato API
        vencidos = []
        for documento in documentos_vencidos:
            fazenda_nome = documento.fazenda.nome if documento.fazenda else None
            fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
            pessoa_nome = documento.pessoa.nome if documento.pessoa else None
            responsavel_nome = documento.responsavel.nome if hasattr(documento, 'responsavel') and documento.responsavel else None

            vencidos.append(
                {
                    "id": documento.id,
                    "nome": documento.nome,
                    "tipo": documento.tipo.value,
                    "data_vencimento": documento.data_vencimento.isoformat() if documento.data_vencimento else None,
                    "fazenda_id": documento.fazenda_id,
                    "fazenda_nome": fazenda_nome,
                    "fazenda_matricula": fazenda_matricula,
                    "pessoa_id": documento.pessoa_id,
                    "pessoa_nome": pessoa_nome,
                    "responsavel_id": getattr(documento, 'responsavel_id', None),
                    "responsavel_nome": responsavel_nome,
                    "emails_notificacao": documento.emails_notificacao,
                    "dias_vencido": abs(documento.proximo_vencimento) if documento.proximo_vencimento else 0,
                    "tem_arquivo": bool(getattr(documento, 'caminho_arquivo', None)),
                }
            )
            
        proximos_vencimento = []
        for documento in documentos_proximos:
            fazenda_nome = documento.fazenda.nome if documento.fazenda else None
            fazenda_matricula = documento.fazenda.matricula if documento.fazenda else None
            pessoa_nome = documento.pessoa.nome if documento.pessoa else None
            responsavel_nome = documento.responsavel.nome if hasattr(documento, 'responsavel') and documento.responsavel else None

            # Calcular próximas notificações
            prazos = documento.prazos_notificacao if documento.prazos_notificacao else [30, 15, 7, 1]
            prazos = [int(p) for p in prazos]
            
            # Obter histórico de notificações enviadas
            enviados = []
            try:
                historico = HistoricoNotificacaoDocumento.query.filter_by(documento_id=documento.id).all()
                for h in historico:
                    enviados.append({
                        "dias_restantes": h.dias_restantes,
                        "data_envio": h.data_envio.isoformat() if h.data_envio else None
                    })
            except Exception as e:
                current_app.logger.warning(f"Erro ao obter histórico: {str(e)}")
                
            proximas_notificacoes = calcular_proximas_notificacoes_programadas(
                documento.data_vencimento, prazos, enviados
            )

            proximos_vencimento.append(
                {
                    "id": documento.id,
                    "nome": documento.nome,
                    "tipo": documento.tipo.value,
                    "data_vencimento": documento.data_vencimento.isoformat() if documento.data_vencimento else None,
                    "dias_restantes": documento.proximo_vencimento,
                    "fazenda_id": documento.fazenda_id,
                    "fazenda_nome": fazenda_nome,
                    "fazenda_matricula": fazenda_matricula,
                    "pessoa_id": documento.pessoa_id,
                    "pessoa_nome": pessoa_nome,
                    "responsavel_id": getattr(documento, 'responsavel_id', None),
                    "responsavel_nome": responsavel_nome,
                    "emails_notificacao": documento.emails_notificacao,
                    "prazos_notificacao": documento.prazos_notificacao,
                    "proximas_notificacoes": proximas_notificacoes,
                    "tem_arquivo": bool(getattr(documento, 'caminho_arquivo', None)),
                }
            )

        return jsonify(
            {
                "vencidos": vencidos, 
                "proximos_vencimento": proximos_vencimento,
                "total_vencidos": len(vencidos),
                "total_proximos": len(proximos_vencimento)
            }
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao listar documentos vencidos: {str(e)}")
        return jsonify({"erro": "Erro ao listar documentos vencidos", "detalhes": str(e)}), 500


@documento_bp.route("/testar-email", methods=["POST"])
def testar_email():
    """
    Envia um e-mail de teste para verificar a configuração.
    
    Returns:
        JSON com resultado do envio
    """
    try:
        dados = request.form if request.form else request.json
        emails = dados.get("emails", "")

        if not emails:
            return jsonify({"sucesso": False, "mensagem": "Nenhum e-mail informado."}), 400

        lista_emails = [email.strip() for email in emails.split(",") if email.strip()]

        if not lista_emails:
            return jsonify({"sucesso": False, "mensagem": "Formato de e-mail inválido."}), 400

        # Usar o serviço de email melhorado
        assunto = "Teste de Notificação - Sistema de Gestão de Documentos"
        corpo_html = """
        <html>
        <body>
            <h2>Teste de Notificação</h2>
            <p>Este é um e-mail de teste enviado pelo sistema de gestão de documentos.</p>
            <p>Se você está recebendo este e-mail, sua configuração de notificações está funcionando corretamente.</p>
            <hr>
            <p><i>Este é um e-mail automático. Por favor, não responda.</i></p>
        </body>
        </html>
        """
        
        # Enviar email usando o serviço
        sucesso = email_service.send_email(
            destinatarios=lista_emails,
            assunto=assunto,
            corpo=corpo_html,
            html=True
        )

        if sucesso:
            mensagem = f"E-mail de teste enviado com sucesso para: {', '.join(lista_emails)}"
            return jsonify({"sucesso": True, "mensagem": mensagem})
        else:
            return jsonify({"sucesso": False, "mensagem": "Falha ao enviar e-mail de teste."}), 500
    except Exception as e:
        current_app.logger.error(f"Erro ao testar envio de e-mail: {str(e)}")
        return jsonify({"sucesso": False, "mensagem": f"Erro ao enviar e-mail de teste: {str(e)}"}), 500


@documento_bp.route("/<int:id>/historico", methods=["GET"])
def obter_historico_notificacoes(id: int):
    """
    Obtém o histórico de notificações de um documento.
    
    Args:
        id: ID do documento
        
    Returns:
        JSON com histórico de notificações
    """
    try:
        documento = Documento.query.get_or_404(id)
        
        # Buscar histórico de notificações
        historico = HistoricoNotificacaoDocumento.obter_historico_documento(id)
        
        # Formatar para resposta
        resultado = []
        for h in historico:
            resultado.append({
                "id": h.id,
                "data_envio": h.data_envio.isoformat() if h.data_envio else None,
                "dias_restantes": h.dias_restantes,
                "destinatarios": h.destinatarios_lista,
                "tipo_notificacao": h.tipo_notificacao,
                "sucesso": h.sucesso,
                "erro_mensagem": h.erro_mensagem
            })
            
        return jsonify({
            "id_documento": id,
            "nome_documento": documento.nome,
            "historico": resultado,
            "total": len(resultado)
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter histórico de notificações: {str(e)}")
        return jsonify({"erro": "Erro ao obter histórico de notificações", "detalhes": str(e)}), 500


# -------- HTML VIEW ROUTES --------

@admin_documentos_bp.route("/vencidos")
@measure_performance()
def vencidos():
    """
    Rota HTML: Tela de documentos vencidos e próximos do vencimento.
    
    Returns:
        Template HTML renderizado
    """
    try:
        # Gerar alertas de vencimento
        documentos_vencidos, documentos_proximos = gerar_alertas_vencimento(mostrar_flash=True)
        
        # Enriquecer dados para renderização
        for doc in documentos_proximos:
            prazos = doc.prazos_notificacao if doc.prazos_notificacao else [30, 15, 7, 1]
            prazos = [int(p) for p in prazos]
            enviados = []
            
            try:
                historico = HistoricoNotificacaoDocumento.query.filter_by(documento_id=doc.id).all()
                for h in historico:
                    enviados.append({
                        "dias_restantes": h.dias_restantes,
                        "data_envio": h.data_envio.isoformat() if h.data_envio else None
                    })
            except Exception as e:
                current_app.logger.warning(f"Erro ao obter histórico: {str(e)}")
                
            doc.proximas_notificacoes = calcular_proximas_notificacoes_programadas(
                doc.data_vencimento, prazos, enviados
            )

        # Renderizar template
        return render_template(
            "admin/documentos/vencidos.html",
            documentos_vencidos=documentos_vencidos,
            documentos_proximos=documentos_proximos,
            agora=datetime.datetime.now(),
        )
    except Exception as e:
        current_app.logger.error(f"Erro na view de documentos vencidos: {str(e)}")
        flash(f"Erro ao carregar documentos vencidos: {str(e)}", "danger")
        return render_template(
            "admin/documentos/vencidos.html", 
            documentos_vencidos=[], 
            documentos_proximos=[]
        )


@admin_documentos_bp.route("/")
@admin_documentos_bp.route("/listar")
@measure_performance()
def listar():
    """
    Rota HTML: Listagem de documentos.
    
    Returns:
        Template HTML renderizado
    """
    try:
        # Parâmetros de filtragem
        tipo = request.args.get('tipo')
        vencidos = request.args.get('vencidos', 'false').lower() == 'true'
        proximos = request.args.get('proximos', 'false').lower() == 'true'
        
        # Construir consulta com filtros
        query = Documento.query.filter(Documento.ativo == True)
        
        if tipo:
            try:
                tipo_enum = TipoDocumento(tipo)
                query = query.filter(Documento.tipo == tipo_enum)
            except ValueError:
                pass
        
        hoje = datetime.date.today()
        
        if vencidos:
            query = query.filter(
                Documento.data_vencimento.isnot(None),
                Documento.data_vencimento < hoje
            )
        elif proximos:
            # Próximos 30 dias
            data_limite = hoje + datetime.timedelta(days=30)
            query = query.filter(
                Documento.data_vencimento.isnot(None),
                Documento.data_vencimento >= hoje,
                Documento.data_vencimento <= data_limite
            )
            
        # Ordenar por vencimento (mais próximos primeiro)
        query = query.order_by(Documento.data_vencimento.asc())
        
        documentos = query.all()
        
        # Obter as opções de tipos
        tipos_documento = [tipo.value for tipo in TipoDocumento]
        
        return render_template(
            "admin/documentos/listar.html",
            documentos=documentos,
            tipos_documento=tipos_documento,
            tipo_filtro=tipo,
            vencidos=vencidos,
            proximos=proximos
        )
    except Exception as e:
        current_app.logger.error(f"Erro na view de listagem de documentos: {str(e)}")
        flash(f"Erro ao carregar documentos: {str(e)}", "danger")
        return render_template(
            "admin/documentos/listar.html",
            documentos=[],
            tipos_documento=[]
        )


@admin_documentos_bp.route("/novo", methods=["GET", "POST"])
def novo():
    """
    Rota HTML: Formulário para cadastro de novo documento.
    
    Returns:
        Template HTML renderizado ou redirecionamento
    """
    if request.method == "POST":
        try:
            # Criar documento via API
            result = criar_documento()
            if isinstance(result, tuple) and result[1] != 201:
                # Erro
                flash(f"Erro ao criar documento: {result[0].json['erro']}", "danger")
                return redirect(request.url)
                
            flash("Documento criado com sucesso!", "success")
            return redirect(url_for("admin_documentos.listar"))
        except Exception as e:
            current_app.logger.error(f"Erro ao criar documento: {str(e)}")
            flash(f"Erro ao criar documento: {str(e)}", "danger")
            
    # Preparar dados para o formulário
    tipos_documento = [tipo.value for tipo in TipoDocumento]
    pessoas = []
    fazendas = []
    responsaveis = []
    
    try:
        from src.models.pessoa import Pessoa
        pessoas = Pessoa.query.all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar pessoas: {str(e)}")
        
    try:
        from src.models.fazenda import Fazenda
        fazendas = Fazenda.query.all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar fazendas: {str(e)}")
        
    try:
        from src.models.usuario import Usuario
        responsaveis = Usuario.query.all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar usuários: {str(e)}")
    
    return render_template(
        "admin/documentos/vencidos.html",
        documentos_vencidos=documentos_vencidos,
        documentos_proximos=documentos_proximos,
    )
