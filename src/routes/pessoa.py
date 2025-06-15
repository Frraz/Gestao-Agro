from flask import Blueprint, request, jsonify, current_app
from src.models.db import db
from src.models.pessoa import Pessoa
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import traceback

pessoa_bp = Blueprint('pessoa', __name__, url_prefix='/api/pessoas')

@pessoa_bp.route('/', methods=['GET'])
def listar_pessoas():
    """Lista todas as pessoas cadastradas."""
    try:
        pessoas = Pessoa.query.all()
        resultado = []
        
        for pessoa in pessoas:
            fazendas = [{'id': f.id, 'nome': f.nome} for f in pessoa.fazendas]
            resultado.append({
                'id': pessoa.id,
                'nome': pessoa.nome,
                'cpf_cnpj': pessoa.cpf_cnpj,
                'email': pessoa.email,
                'telefone': pessoa.telefone,
                'endereco': pessoa.endereco,
                'fazendas': fazendas
            })
        
        return jsonify(resultado)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar pessoas: {str(e)}")
        return jsonify({'erro': 'Erro ao listar pessoas', 'detalhes': str(e)}), 500

@pessoa_bp.route('/<int:id>', methods=['GET'])
def obter_pessoa(id):
    """Obtém detalhes de uma pessoa específica."""
    try:
        pessoa = Pessoa.query.get_or_404(id)
        fazendas = [{'id': f.id, 'nome': f.nome} for f in pessoa.fazendas]
        
        return jsonify({
            'id': pessoa.id,
            'nome': pessoa.nome,
            'cpf_cnpj': pessoa.cpf_cnpj,
            'email': pessoa.email,
            'telefone': pessoa.telefone,
            'endereco': pessoa.endereco,
            'fazendas': fazendas
        })
    except Exception as e:
        current_app.logger.error(f"Erro ao obter pessoa {id}: {str(e)}")
        return jsonify({'erro': f'Erro ao obter pessoa {id}', 'detalhes': str(e)}), 500

@pessoa_bp.route('/', methods=['POST'])
def criar_pessoa():
    """Cria uma nova pessoa."""
    try:
        dados = request.json
        
        # Validação de campos obrigatórios
        if not dados:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
            
        if not dados.get('nome'):
            return jsonify({'erro': 'Nome é obrigatório'}), 400
            
        if not dados.get('cpf_cnpj'):
            return jsonify({'erro': 'CPF/CNPJ é obrigatório'}), 400
        
        # Verifica se já existe pessoa com o mesmo CPF/CNPJ
        if Pessoa.query.filter_by(cpf_cnpj=dados.get('cpf_cnpj')).first():
            return jsonify({'erro': 'CPF/CNPJ já cadastrado'}), 400
        
        # Validação do formato de CPF/CNPJ
        cpf_cnpj = dados.get('cpf_cnpj').replace('.', '').replace('-', '').replace('/', '')
        if not (len(cpf_cnpj) == 11 or len(cpf_cnpj) == 14):
            return jsonify({'erro': 'Formato de CPF/CNPJ inválido'}), 400
        
        # Validação de email (se fornecido)
        if dados.get('email') and '@' not in dados.get('email'):
            return jsonify({'erro': 'Formato de email inválido'}), 400
        
        nova_pessoa = Pessoa(
            nome=dados.get('nome'),
            cpf_cnpj=dados.get('cpf_cnpj'),
            email=dados.get('email'),
            telefone=dados.get('telefone'),
            endereco=dados.get('endereco')
        )
        
        db.session.add(nova_pessoa)
        db.session.commit()
        
        current_app.logger.info(f"Pessoa criada com sucesso: {nova_pessoa.nome} (ID: {nova_pessoa.id})")
        
        return jsonify({
            'id': nova_pessoa.id,
            'nome': nova_pessoa.nome,
            'cpf_cnpj': nova_pessoa.cpf_cnpj,
            'email': nova_pessoa.email,
            'telefone': nova_pessoa.telefone,
            'endereco': nova_pessoa.endereco
        }), 201
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de integridade ao criar pessoa: {str(e)}")
        return jsonify({'erro': 'Erro de integridade no banco de dados', 'detalhes': str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de banco de dados ao criar pessoa: {str(e)}")
        return jsonify({'erro': 'Erro de banco de dados', 'detalhes': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar pessoa: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'erro': 'Erro ao criar pessoa', 'detalhes': str(e)}), 500

@pessoa_bp.route('/<int:id>', methods=['PUT'])
def atualizar_pessoa(id):
    """Atualiza os dados de uma pessoa existente."""
    try:
        pessoa = Pessoa.query.get_or_404(id)
        dados = request.json
        
        if not dados:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        # Verifica se o CPF/CNPJ já existe para outra pessoa
        if dados.get('cpf_cnpj') and dados.get('cpf_cnpj') != pessoa.cpf_cnpj:
            pessoa_existente = Pessoa.query.filter_by(cpf_cnpj=dados.get('cpf_cnpj')).first()
            if pessoa_existente and pessoa_existente.id != id:
                return jsonify({'erro': 'CPF/CNPJ já cadastrado para outra pessoa'}), 400
            
            # Validação do formato de CPF/CNPJ
            cpf_cnpj = dados.get('cpf_cnpj').replace('.', '').replace('-', '').replace('/', '')
            if not (len(cpf_cnpj) == 11 or len(cpf_cnpj) == 14):
                return jsonify({'erro': 'Formato de CPF/CNPJ inválido'}), 400
        
        # Validação de email (se fornecido)
        if dados.get('email') and '@' not in dados.get('email'):
            return jsonify({'erro': 'Formato de email inválido'}), 400
        
        # Atualiza os campos
        if dados.get('nome'):
            pessoa.nome = dados.get('nome')
        if dados.get('cpf_cnpj'):
            pessoa.cpf_cnpj = dados.get('cpf_cnpj')
        if 'email' in dados:
            pessoa.email = dados.get('email')
        if 'telefone' in dados:
            pessoa.telefone = dados.get('telefone')
        if 'endereco' in dados:
            pessoa.endereco = dados.get('endereco')
        
        db.session.commit()
        
        current_app.logger.info(f"Pessoa atualizada com sucesso: {pessoa.nome} (ID: {pessoa.id})")
        
        return jsonify({
            'id': pessoa.id,
            'nome': pessoa.nome,
            'cpf_cnpj': pessoa.cpf_cnpj,
            'email': pessoa.email,
            'telefone': pessoa.telefone,
            'endereco': pessoa.endereco
        })
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de integridade ao atualizar pessoa {id}: {str(e)}")
        return jsonify({'erro': 'Erro de integridade no banco de dados', 'detalhes': str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de banco de dados ao atualizar pessoa {id}: {str(e)}")
        return jsonify({'erro': 'Erro de banco de dados', 'detalhes': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar pessoa {id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'erro': 'Erro ao atualizar pessoa', 'detalhes': str(e)}), 500

@pessoa_bp.route('/<int:id>', methods=['DELETE'])
def excluir_pessoa(id):
    """Exclui uma pessoa do sistema."""
    try:
        pessoa = Pessoa.query.get_or_404(id)
        
        # Verificar se a pessoa tem documentos associados
        if hasattr(pessoa, 'documentos') and pessoa.documentos and len(pessoa.documentos) > 0:
            return jsonify({'erro': 'Não é possível excluir a pessoa pois existem documentos associados a ela'}), 400
        
        # Verificar se a pessoa tem fazendas associadas
        if pessoa.fazendas and len(pessoa.fazendas) > 0:
            # Remover associações com fazendas
            pessoa.fazendas = []
        
        nome = pessoa.nome
        db.session.delete(pessoa)
        db.session.commit()
        
        current_app.logger.info(f"Pessoa excluída com sucesso: {nome} (ID: {id})")
        
        return jsonify({'mensagem': f'Pessoa {nome} excluída com sucesso'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de banco de dados ao excluir pessoa {id}: {str(e)}")
        return jsonify({'erro': 'Erro de banco de dados ao excluir pessoa', 'detalhes': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir pessoa {id}: {str(e)}")
        return jsonify({'erro': 'Erro ao excluir pessoa', 'detalhes': str(e)}), 500

@pessoa_bp.route('/<int:id>/fazendas', methods=['GET'])
def listar_fazendas_pessoa(id):
    """Lista todas as fazendas associadas a uma pessoa."""
    try:
        pessoa = Pessoa.query.get_or_404(id)
        fazendas = []
        
        for fazenda in pessoa.fazendas:
            fazendas.append({
                'id': fazenda.id,
                'nome': fazenda.nome,
                'matricula': fazenda.matricula,
                'tamanho_total': fazenda.tamanho_total,
                'area_consolidada': fazenda.area_consolidada,
                'tamanho_disponivel': fazenda.tamanho_disponivel,
                'tipo_posse': fazenda.tipo_posse.value,
                'municipio': fazenda.municipio,
                'estado': fazenda.estado,
                'recibo_car': fazenda.recibo_car
            })
        
        return jsonify(fazendas)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar fazendas da pessoa {id}: {str(e)}")
        return jsonify({'erro': f'Erro ao listar fazendas da pessoa {id}', 'detalhes': str(e)}), 500

@pessoa_bp.route('/<int:pessoa_id>/fazendas/<int:fazenda_id>', methods=['POST'])
def associar_fazenda(pessoa_id, fazenda_id):
    """Associa uma fazenda a uma pessoa."""
    try:
        from src.models.fazenda import Fazenda
        
        pessoa = Pessoa.query.get_or_404(pessoa_id)
        fazenda = Fazenda.query.get_or_404(fazenda_id)
        
        if fazenda in pessoa.fazendas:
            return jsonify({'mensagem': 'Fazenda já associada a esta pessoa'}), 400
        
        pessoa.fazendas.append(fazenda)
        db.session.commit()
        
        current_app.logger.info(f"Fazenda {fazenda.nome} (ID: {fazenda_id}) associada à pessoa {pessoa.nome} (ID: {pessoa_id})")
        
        return jsonify({'mensagem': f'Fazenda {fazenda.nome} associada à pessoa {pessoa.nome} com sucesso'}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de banco de dados ao associar fazenda {fazenda_id} à pessoa {pessoa_id}: {str(e)}")
        return jsonify({'erro': 'Erro de banco de dados ao associar fazenda', 'detalhes': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao associar fazenda {fazenda_id} à pessoa {pessoa_id}: {str(e)}")
        return jsonify({'erro': 'Erro ao associar fazenda à pessoa', 'detalhes': str(e)}), 500

@pessoa_bp.route('/<int:pessoa_id>/fazendas/<int:fazenda_id>', methods=['DELETE'])
def desassociar_fazenda(pessoa_id, fazenda_id):
    """Remove a associação entre uma pessoa e uma fazenda."""
    try:
        from src.models.fazenda import Fazenda
        
        pessoa = Pessoa.query.get_or_404(pessoa_id)
        fazenda = Fazenda.query.get_or_404(fazenda_id)
        
        if fazenda not in pessoa.fazendas:
            return jsonify({'erro': 'Fazenda não está associada a esta pessoa'}), 400
        
        pessoa.fazendas.remove(fazenda)
        db.session.commit()
        
        current_app.logger.info(f"Associação entre pessoa {pessoa.nome} (ID: {pessoa_id}) e fazenda {fazenda.nome} (ID: {fazenda_id}) removida")
        
        return jsonify({'mensagem': f'Associação entre {pessoa.nome} e fazenda {fazenda.nome} removida com sucesso'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erro de banco de dados ao desassociar fazenda {fazenda_id} da pessoa {pessoa_id}: {str(e)}")
        return jsonify({'erro': 'Erro de banco de dados ao desassociar fazenda', 'detalhes': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao desassociar fazenda {fazenda_id} da pessoa {pessoa_id}: {str(e)}")
        return jsonify({'erro': 'Erro ao desassociar fazenda da pessoa', 'detalhes': str(e)}), 500

@pessoa_bp.route('/<int:id>/documentos', methods=['GET'])
def listar_documentos_pessoa(id):
    """Lista todos os documentos associados a uma pessoa."""
    try:
        pessoa = Pessoa.query.get_or_404(id)
        documentos = []
        
        for documento in pessoa.documentos:
            documentos.append({
                'id': documento.id,
                'nome': documento.nome,
                'tipo': documento.tipo.value,
                'data_emissao': documento.data_emissao.isoformat(),
                'data_vencimento': documento.data_vencimento.isoformat() if documento.data_vencimento else None,
                'emails_notificacao': documento.emails_notificacao,
                'prazos_notificacao': documento.prazos_notificacao,
                'esta_vencido': documento.esta_vencido,
                'proximo_vencimento': documento.proximo_vencimento
            })
        
        return jsonify(documentos)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar documentos da pessoa {id}: {str(e)}")
        return jsonify({'erro': f'Erro ao listar documentos da pessoa {id}', 'detalhes': str(e)}), 500
