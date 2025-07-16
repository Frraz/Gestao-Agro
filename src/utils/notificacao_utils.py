# /src/utils/notificacao_utils.py

from datetime import datetime, timedelta, time

def calcular_proximas_notificacoes_programadas(data_vencimento, prazos, enviados=None):
    """
    Retorna uma lista ordenada de próximas notificações programadas.
    :param data_vencimento: datetime.date ou datetime.datetime
    :param prazos: lista de inteiros (dias de antecedência)
    :param enviados: lista de prazos já notificados (opcional)
    """
    if enviados is None:
        enviados = []
    agora = datetime.now()
    if isinstance(data_vencimento, datetime):
        venc = data_vencimento
    else:
        venc = datetime.combine(data_vencimento, time(8, 0))  # Corrigido para 08:00
    futuras = []
    for prazo in prazos:
        if prazo in enviados:
            continue
        envio = venc - timedelta(days=prazo)
        if envio > agora:
            delta = envio - agora
            dias = delta.days
            horas, resto = divmod(delta.seconds, 3600)
            minutos = resto // 60
            if dias > 0:
                texto = f"{dias} d {horas}h {minutos}m para enviar a notificação"
            else:
                texto = f"{horas}h {minutos}m para enviar a notificação"
            futuras.append({
                "prazo": prazo,
                "envio": envio,
                "restante_texto": texto,
                "restante_delta": delta,
            })
    futuras.sort(key=lambda x: x["envio"])
    return futuras