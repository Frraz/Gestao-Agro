# /src/utils/notificacao_utils.py

"""
Utilitários para gerenciamento de notificações
Fornece funções auxiliares para cálculo de datas, formatação e manipulação de notificações
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Union, Optional

def calcular_proximas_notificacoes_programadas(
    data_vencimento: Union[date, datetime], 
    prazos: List[int], 
    enviados: Optional[List[int]] = None,
    hora_envio: time = time(8, 0)
) -> List[Dict[str, Any]]:
    """
    Retorna uma lista ordenada de próximas notificações programadas.
    
    Args:
        data_vencimento: Data de vencimento (date ou datetime)
        prazos: Lista de dias de antecedência para notificar (ex: [30, 15, 7, 1])
        enviados: Lista opcional de prazos já notificados para ignorar
        hora_envio: Horário do dia para enviar as notificações
    
    Returns:
        Lista de dicionários contendo informações das próximas notificações
    """
    if enviados is None:
        enviados = []
    
    # Obter data/hora atual
    agora = datetime.now()
    
    # Normalizar data de vencimento para datetime com hora de envio
    if isinstance(data_vencimento, datetime):
        venc = data_vencimento
    else:
        # Combina data com hora de envio
        venc = datetime.combine(data_vencimento, hora_envio)
    
    futuras = []
    for prazo in sorted(prazos, reverse=True):  # Ordenar prazos do maior para o menor
        if prazo in enviados:
            continue
            
        # Calcular data de envio da notificação
        envio = venc - timedelta(days=prazo)
        
        # Só incluir notificações futuras
        if envio > agora:
            delta = envio - agora
            dias = delta.days
            horas, resto = divmod(delta.seconds, 3600)
            minutos = resto // 60
            
            # Calcular data de vencimento relativa em relação ao prazo
            venc_em = "hoje" if prazo == 0 else f"em {prazo} dia{'s' if prazo != 1 else ''}"
            
            # Formatar texto de tempo restante
            if dias > 0:
                texto = f"{dias} dia{'s' if dias != 1 else ''} {horas}h {minutos}m para enviar"
            elif horas > 0:
                texto = f"{horas}h {minutos}m para enviar"
            else:
                texto = f"{minutos}m para enviar"
            
            futuras.append({
                "prazo": prazo,
                "envio": envio,
                "data_envio": envio.strftime("%d/%m/%Y"),
                "hora_envio": envio.strftime("%H:%M"),
                "vencimento_em": venc_em,
                "restante_texto": texto,
                "restante_delta": delta,
                "restante_segundos": delta.total_seconds(),
            })
    
    # Ordenar por data de envio (mais próxima primeiro)
    futuras.sort(key=lambda x: x["envio"])
    return futuras


def formatar_data_notificacao(dt: Optional[datetime], formato: str = "%d/%m/%Y %H:%M") -> str:
    """
    Formata uma data/hora para exibição, com tratamento para valores nulos
    
    Args:
        dt: Data/hora para formatar
        formato: String de formato (padrão dia/mês/ano hora:minuto)
        
    Returns:
        String formatada ou 'N/A' se dt for None
    """
    if not dt:
        return "N/A"
    return dt.strftime(formato)


def calcular_vencidos_para_hoje(
    notificacoes: List[Dict[str, Any]], 
    campo_data_vencimento: str = "data_vencimento"
) -> List[Dict[str, Any]]:
    """
    Filtra uma lista de notificações retornando apenas as vencidas hoje
    
    Args:
        notificacoes: Lista de dicionários com campo de data de vencimento
        campo_data_vencimento: Nome da chave contendo a data de vencimento
        
    Returns:
        Lista filtrada com apenas notificações vencidas hoje
    """
    hoje = date.today()
    
    vencidos_hoje = []
    for notificacao in notificacoes:
        venc = notificacao.get(campo_data_vencimento)
        if venc:
            if isinstance(venc, datetime):
                venc_date = venc.date()
            elif isinstance(venc, date):
                venc_date = venc
            else:
                continue
                
            if venc_date == hoje:
                vencidos_hoje.append(notificacao)
                
    return vencidos_hoje


def calcular_dias_restantes(data_vencimento: Union[date, datetime]) -> int:
    """
    Calcula quantos dias faltam para uma data de vencimento
    
    Args:
        data_vencimento: Data de vencimento a ser verificada
        
    Returns:
        Número de dias até o vencimento (negativo se já venceu)
    """
    hoje = date.today()
    
    if isinstance(data_vencimento, datetime):
        venc = data_vencimento.date()
    else:
        venc = data_vencimento
        
    return (venc - hoje).days


def agrupar_por_prazo(
    itens: List[Dict[str, Any]], 
    campo_data_vencimento: str = "data_vencimento"
) -> Dict[int, List]:
    """
    Agrupa uma lista de itens por prazos comuns de notificação (30, 15, 7, etc)
    
    Args:
        itens: Lista de dicionários com campo de data de vencimento
        campo_data_vencimento: Nome da chave contendo a data de vencimento
        
    Returns:
        Dicionário onde as chaves são os prazos em dias e os valores são listas de itens
    """
    hoje = date.today()
    
    # Prazos comuns para notificações
    prazos_comuns = [1, 3, 7, 15, 30, 60, 90]
    
    # Inicializar dicionário de resultado
    resultado = {prazo: [] for prazo in prazos_comuns}
    resultado[0] = []  # Vencendo hoje
    resultado[-1] = []  # Vencidos
    
    for item in itens:
        venc = item.get(campo_data_vencimento)
        if venc:
            if isinstance(venc, datetime):
                venc_date = venc.date()
            elif isinstance(venc, date):
                venc_date = venc
            else:
                continue
                
            # Calcular dias restantes
            dias = (venc_date - hoje).days
            
            # Agrupar
            if dias < 0:
                resultado[-1].append(item)
            elif dias == 0:
                resultado[0].append(item)
            else:
                # Encontrar o prazo mais próximo
                for prazo in prazos_comuns:
                    if dias <= prazo:
                        resultado[prazo].append(item)
                        break
    
    # Remover prazos vazios
    return {k: v for k, v in resultado.items() if v}


def criar_mensagem_status(
    proximas: List[Dict[str, Any]], 
    total: int, 
    nome_sistema: str = "Sistema"
) -> Dict[str, Any]:
    """
    Cria uma mensagem formatada sobre o status das notificações
    
    Args:
        proximas: Lista de próximas notificações
        total: Total de notificações no sistema
        nome_sistema: Nome do sistema para exibição
        
    Returns:
        Dicionário com mensagem formatada e dados
    """
    hoje = datetime.now()
    
    if not proximas:
        return {
            "status": "ok",
            "mensagem": f"Não há notificações pendentes no momento.",
            "stats": {
                "total": total,
                "proximas": 0
            },
            "timestamp": hoje.isoformat(),
            "proximas": []
        }
    
    # Obter próxima notificação
    proxima = proximas[0]
    
    # Criar mensagem
    if len(proximas) == 1:
        mensagem = f"Próxima notificação: {proxima['restante_texto']} ({proxima['vencimento_em']})"
    else:
        mensagem = f"{len(proximas)} notificações programadas. Próxima: {proxima['restante_texto']} ({proxima['vencimento_em']})"
    
    return {
        "status": "ok",
        "mensagem": mensagem,
        "stats": {
            "total": total,
            "proximas": len(proximas)
        },
        "timestamp": hoje.isoformat(),
        "proximas": proximas
    }


def obter_status_vencimento(dias_restantes: int) -> Dict[str, Any]:
    """
    Retorna informações formatadas sobre status de vencimento
    
    Args:
        dias_restantes: Número de dias até o vencimento
        
    Returns:
        Dicionário com informações de status (classe CSS, texto, etc)
    """
    if dias_restantes < 0:
        return {
            "status": "vencido",
            "classe": "danger",
            "texto": f"Vencido há {abs(dias_restantes)} dia{'s' if abs(dias_restantes) != 1 else ''}",
            "badge": "danger",
            "icone": "exclamation-circle",
            "dias": dias_restantes
        }
    elif dias_restantes == 0:
        return {
            "status": "hoje",
            "classe": "danger",
            "texto": "Vence hoje",
            "badge": "danger",
            "icone": "exclamation-circle",
            "dias": 0
        }
    elif dias_restantes <= 3:
        return {
            "status": "urgente",
            "classe": "danger",
            "texto": f"Vence em {dias_restantes} dia{'s' if dias_restantes != 1 else ''}",
            "badge": "danger",
            "icone": "exclamation-triangle",
            "dias": dias_restantes
        }
    elif dias_restantes <= 7:
        return {
            "status": "alerta",
            "classe": "warning",
            "texto": f"Vence em {dias_restantes} dias",
            "badge": "warning",
            "icone": "exclamation-triangle",
            "dias": dias_restantes
        }
    elif dias_restantes <= 30:
        return {
            "status": "atencao",
            "classe": "info",
            "texto": f"Vence em {dias_restantes} dias",
            "badge": "info",
            "icone": "info-circle",
            "dias": dias_restantes
        }
    else:
        return {
            "status": "normal",
            "classe": "success",
            "texto": f"Vence em {dias_restantes} dias",
            "badge": "success",
            "icone": "calendar-check",
            "dias": dias_restantes
        }


# Exportar funções principais
__all__ = [
    'calcular_proximas_notificacoes_programadas',
    'formatar_data_notificacao',
    'calcular_vencidos_para_hoje',
    'calcular_dias_restantes',
    'agrupar_por_prazo',
    'criar_mensagem_status',
    'obter_status_vencimento'
]