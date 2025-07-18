# /src/utils/notificacao_utils.py

"""
Utilitários para gerenciamento de notificações
Fornece funções auxiliares para cálculo de datas, formatação e manipulação de notificações
"""


def calcular_proximas_notificacoes_programadas(data_vencimento, prazos, enviados=None):
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
