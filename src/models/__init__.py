# /src/models/__init__.py

"""
Módulo de inicialização para os modelos do sistema.

Este pacote importa e expõe todas as classes de modelo relacionadas ao domínio da aplicação,
incluindo pessoas, fazendas, documentos, endividamentos e notificações.
"""

from .documento import Documento, TipoDocumento
from .endividamento import Endividamento, EndividamentoFazenda, Parcela
from .fazenda import Fazenda

from .notificacao_endividamento import (HistoricoNotificacao,
                                        NotificacaoEndividamento)

from .pessoa import Pessoa
from .pessoa_fazenda import PessoaFazenda, TipoPosse

__all__ = [
    "Pessoa",
    "Fazenda",
    "PessoaFazenda",
    "TipoPosse",
    "Documento",
    "TipoDocumento",
    "Endividamento",
    "EndividamentoFazenda",
    "Parcela",
    "NotificacaoEndividamento",
    "HistoricoNotificacao",
]