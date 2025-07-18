# src/utils/notificacao_utils.py

"""
Utilitários para notificações e cálculo de datas de vencimento
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Union, Optional, Tuple


def calcular_proximas_notificacoes_programadas(data_vencimento: date, prazos: List[int], 
                                              enviados: List[int] = None) -> List[Dict[str, Any]]:
    """
    Calcula as próximas datas para notificações programadas
    
    Args:
        data_vencimento: Data de vencimento
        prazos: Lista de prazos em dias (ex: [30, 15, 7, 3, 1])
        enviados: Lista de prazos que já foram enviados
        
    Returns:
        Lista de dicionários com informações de notificações
    """
    enviados = enviados or []
    hoje = date.today()
    proximas = []
    
    for prazo in sorted(prazos, reverse=True):  # Ordenar decrescente para enviar notificações mais distantes primeiro
        if prazo in enviados:
            continue
        
        data_notificacao = data_vencimento - timedelta(days=prazo)
        
        # Se a data já passou, não incluir
        if data_notificacao < hoje:
            continue
            
        # Calcular data/hora de envio (9h da manhã no fuso padrão)
        data_hora_envio = datetime.combine(
            data_notificacao, 
            datetime.min.time().replace(hour=9)
        )
        
        proximas.append({
            'prazo': prazo,
            'data': data_notificacao,
            'envio': data_hora_envio
        })
    
    return proximas


def calcular_dias_restantes(data_vencimento: Union[date, datetime], data_base: Union[date, datetime] = None) -> int:
    """
    Calcula quantos dias faltam para o vencimento a partir de uma data base
    
    Args:
        data_vencimento: Data de vencimento
        data_base: Data base para cálculo (padrão: hoje)
        
    Returns:
        Número de dias até o vencimento (negativo se já venceu)
    """
    # Converter para date se for datetime
    if isinstance(data_vencimento, datetime):
        data_vencimento = data_vencimento.date()
        
    # Se não for especificada data base, usar hoje
    if data_base is None:
        data_base = date.today()
    elif isinstance(data_base, datetime):
        data_base = data_base.date()
    
    # Calcular diferença em dias
    delta = data_vencimento - data_base
    return delta.days


def obter_status_vencimento(data_vencimento: Union[date, datetime], 
                          data_base: Union[date, datetime] = None) -> Tuple[str, int]:
    """
    Retorna o status de vencimento de um documento ou compromisso
    
    Args:
        data_vencimento: Data de vencimento do documento/compromisso
        data_base: Data base para cálculo (padrão: hoje)
        
    Returns:
        Tupla com (status, dias_restantes)
        Status pode ser: 'vencido', 'urgente', 'atencao', 'proximo', 'em_dia'
    """
    dias = calcular_dias_restantes(data_vencimento, data_base)
    
    if dias < 0:
        return 'vencido', dias
    elif dias <= 3:
        return 'urgente', dias
    elif dias <= 7:
        return 'atencao', dias
    elif dias <= 30:
        return 'proximo', dias
    else:
        return 'em_dia', dias


def formatar_periodo_vencimento(dias: int) -> str:
    """
    Formata o período de vencimento em texto amigável
    
    Args:
        dias: Número de dias até o vencimento (negativo se já venceu)
        
    Returns:
        Texto formatado do período
    """
    if dias < 0:
        if dias == -1:
            return "Vencido ontem"
        return f"Vencido há {abs(dias)} dias"
    elif dias == 0:
        return "Vence hoje"
    elif dias == 1:
        return "Vence amanhã"
    elif dias < 30:
        return f"Vence em {dias} dias"
    elif dias < 60:
        return "Vence em 1 mês"
    elif dias < 365:
        meses = dias // 30
        return f"Vence em {meses} meses"
    else:
        anos = dias // 365
        meses = (dias % 365) // 30
        if meses > 0:
            return f"Vence em {anos} ano{'s' if anos > 1 else ''} e {meses} {'meses' if meses > 1 else 'mês'}"
        return f"Vence em {anos} ano{'s' if anos > 1 else ''}"


def formatar_email_notificacao(
    titulo: str, 
    corpo: str, 
    detalhes: Optional[Dict[str, Any]] = None,
    botoes: Optional[List[Dict[str, str]]] = None,
    tipo: str = 'padrao'
) -> str:
    """
    Formata um e-mail de notificação em HTML
    
    Args:
        titulo: Título da notificação
        corpo: Corpo da mensagem (pode conter HTML)
        detalhes: Dicionário com detalhes adicionais para exibir (chave: valor)
        botoes: Lista de botões de ação [{"texto": "Texto do botão", "url": "URL"}]
        tipo: Tipo de notificação ('padrao', 'alerta', 'urgente', 'sucesso')
        
    Returns:
        String HTML formatada para envio por e-mail
    """
    # Definir cores baseadas no tipo
    if tipo == 'urgente':
        cor_cabecalho = "#d32f2f"  # Vermelho
        cor_botao = "#d32f2f"
    elif tipo == 'alerta':
        cor_cabecalho = "#ff9800"  # Laranja
        cor_botao = "#ff9800"
    elif tipo == 'sucesso':
        cor_cabecalho = "#4caf50"  # Verde
        cor_botao = "#4caf50"
    else:  # padrao
        cor_cabecalho = "#1976d2"  # Azul
        cor_botao = "#1976d2"
    
    # Preparar seção de detalhes se fornecida
    detalhes_html = ""
    if detalhes:
        detalhes_itens = []
        for chave, valor in detalhes.items():
            detalhes_itens.append(f"<tr><td><strong>{chave}:</strong></td><td>{valor}</td></tr>")
        
        detalhes_html = f"""
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            {''.join(detalhes_itens)}
        </table>
        """
    
    # Preparar botões de ação
    botoes_html = ""
    if botoes:
        botoes_itens = []
        for botao in botoes:
            botoes_itens.append(
                f"""<a href="{botao.get('url', '#')}" 
                    style="display: inline-block; padding: 10px 16px; margin: 5px; 
                    background-color: {cor_botao}; color: white; text-decoration: none; 
                    border-radius: 4px;">{botao.get('texto', 'Visualizar')}</a>"""
            )
        
        botoes_html = f"""
        <div style="text-align: center; margin: 30px 0;">
            {''.join(botoes_itens)}
        </div>
        """
    
    # Gerar HTML do e-mail
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{titulo}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; color: #333333; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
            <!-- Cabeçalho -->
            <div style="background-color: {cor_cabecalho}; padding: 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0;">{titulo}</h1>
            </div>
            
            <!-- Conteúdo -->
            <div style="padding: 20px;">
                <div style="line-height: 1.6;">
                    {corpo}
                </div>
                
                {detalhes_html}
                
                {botoes_html}
                
                <hr style="border: none; border-top: 1px solid #eeeeee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #777777; text-align: center;">
                    Esta mensagem foi enviada pelo Sistema de Gestão Agrícola.<br>
                    Por favor, não responda diretamente a este e-mail.
                </p>
            </div>
        </div>
    </body>
    </html>
    """