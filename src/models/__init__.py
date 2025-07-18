# /src/models/__init__.py

"""
Módulo de inicialização para os modelos do sistema.

Este pacote importa e expõe todas as classes de modelo relacionadas ao domínio da aplicação,
incluindo pessoas, fazendas, documentos, endividamentos e notificações.
"""

from .documento import Documento, TipoDocumento
from .endividamento import Endividamento, EndividamentoFazenda, Parcela
from .fazenda import Fazenda, TipoPosse
from .notificacao_endividamento import NotificacaoEndividamento
from .pessoa import Pessoa

__all__ = [
    "Pessoa",
    "Fazenda",
    "TipoPosse",
    "Documento",
    "TipoDocumento",
    "Endividamento",
    "EndividamentoFazenda",
    "Parcela",
    "NotificacaoEndividamento",
]