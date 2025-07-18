# /src/utils/notificacoes.py

"""
Utilitários para gerenciamento e exibição de notificações e alertas
relacionados aos documentos e seus vencimentos.
"""

from flask import current_app, flash
from sqlalchemy import and_, or_, func

from src.models.documento import Documento
from src.utils.notificacao_utils import obter_status_vencimento, calcular_dias_restantes


def verificar_documentos_vencimento(filtro_dias: int = 90) -> Tuple[List[Documento], List[Documento]]:
    """
    Verifica documentos vencidos ou próximos do vencimento.
    Esta função é chamada quando o usuário acessa o dashboard ou a página de vencimentos.

    Args:
        filtro_dias: Buscar apenas documentos que vencem em até X dias

    Returns:
        Tupla (documentos_vencidos, documentos_proximos_vencimento)
    """
    try:
        hoje = datetime.date.today()
        data_limite = hoje + datetime.timedelta(days=filtro_dias)
        
        # Buscar documentos com data de vencimento que estão no período relevante
        documentos = Documento.query.filter(
            Documento.data_vencimento.isnot(None),
            or_(
                Documento.data_vencimento <= hoje,  # Vencidos
                and_(
                    Documento.data_vencimento > hoje,
                    Documento.data_vencimento <= data_limite  # Próximos do vencimento
                )
            )
        ).order_by(Documento.data_vencimento).all()

        # Separar documentos vencidos e próximos do vencimento
        documentos_vencidos = []
        documentos_proximos = []

        for documento in documentos:
            if documento.data_vencimento <= hoje:
                documentos_vencidos.append(documento)
            elif hasattr(documento, 'precisa_notificar') and documento.precisa_notificar:
                documentos_proximos.append(documento)
            else:
                # Verificar se está próximo do vencimento pelos prazos padrão
                dias_restantes = calcular_dias_restantes(documento.data_vencimento)
                if dias_restantes <= 30:  # Notificar documentos com menos de 30 dias
                    documentos_proximos.append(documento)

        return documentos_vencidos, documentos_proximos

    except Exception as e:
        current_app.logger.error(f"Erro ao verificar documentos vencidos: {str(e)}", exc_info=True)
        return [], []


def gerar_alertas_vencimento(mostrar_flash: bool = True) -> Tuple[List[Documento], List[Documento]]:
    """
    Gera alertas para exibição na interface sobre documentos vencidos ou próximos do vencimento.
    
    Args:
        mostrar_flash: Se True, exibe alertas flash na interface
        
    Returns:
        Tupla (documentos_vencidos, documentos_proximos)
    """
    documentos_vencidos, documentos_proximos = verificar_documentos_vencimento()

    # Gerar alertas para documentos vencidos
    if documentos_vencidos and mostrar_flash:
        flash(
            f"Atenção! Existem {len(documentos_vencidos)} documento(s) vencido(s). "
            f'<a href="/admin/documentos/vencidos" class="alert-link">Verificar agora</a>',
            "danger",
        )

    # Gerar alertas para documentos próximos do vencimento
    if documentos_proximos and mostrar_flash:
        flash(
            f"Existem {len(documentos_proximos)} documento(s) próximo(s) do vencimento. "
            f'<a href="/admin/documentos/vencidos" class="alert-link">Verificar agora</a>',
            "warning",
        )

    return documentos_vencidos, documentos_proximos


def agrupar_documentos_por_prazo(documentos: List[Documento]) -> Dict[str, List[Documento]]:
    """
    Agrupa documentos por prazo de vencimento para facilitar a exibição.
    
    Args:
        documentos: Lista de documentos para agrupar
        
    Returns:
        Dicionário com documentos agrupados por prazo
    """
    hoje = datetime.date.today()
    
    agrupados = {
        "vencidos": [],
        "hoje": [],
        "7_dias": [],
        "30_dias": [],
        "outros": []
    }
    
    for documento in documentos:
        if not documento.data_vencimento:
            continue
            
        dias = (documento.data_vencimento - hoje).days
        
        if dias < 0:
            agrupados["vencidos"].append(documento)
        elif dias == 0:
            agrupados["hoje"].append(documento)
        elif dias <= 7:
            agrupados["7_dias"].append(documento)
        elif dias <= 30:
            agrupados["30_dias"].append(documento)
        else:
            agrupados["outros"].append(documento)
            
    return {k: v for k, v in agrupados.items() if v}


def contar_documentos_por_vencimento() -> Dict[str, int]:
    """
    Conta documentos por categoria de vencimento.
    
    Returns:
        Dicionário com contagem por categoria
    """
    try:
        hoje = datetime.date.today()
        
        # Contar documentos vencidos
        vencidos = Documento.query.filter(
            Documento.data_vencimento < hoje
        ).count()
        
        # Contar documentos que vencem hoje
        hoje_count = Documento.query.filter(
            Documento.data_vencimento == hoje
        ).count()
        
        # Contar documentos que vencem em até 7 dias
        semana = Documento.query.filter(
            Documento.data_vencimento > hoje,
            Documento.data_vencimento <= hoje + datetime.timedelta(days=7)
        ).count()
        
        # Contar documentos que vencem em até 30 dias
        mes = Documento.query.filter(
            Documento.data_vencimento > hoje + datetime.timedelta(days=7),
            Documento.data_vencimento <= hoje + datetime.timedelta(days=30)
        ).count()
        
        # Contar total de documentos com vencimento
        total = Documento.query.filter(
            Documento.data_vencimento.isnot(None)
        ).count()
        
        return {
            "vencidos": vencidos,
            "hoje": hoje_count,
            "7_dias": semana,
            "30_dias": mes,
            "total": total
        }
        
    except Exception as e:
        current_app.logger.error(f"Erro ao contar documentos por vencimento: {str(e)}")
        return {
            "vencidos": 0, 
            "hoje": 0,
            "7_dias": 0,
            "30_dias": 0,
            "total": 0
        }


def formatar_resumo_vencimentos(contador: Dict[str, int]) -> str:
    """
    Formata um resumo de vencimentos para exibição.
    
    Args:
        contador: Dicionário com contagem de documentos
        
    Returns:
        String formatada com resumo
    """
    resumo = []
    
    if contador["vencidos"] > 0:
        resumo.append(f"<strong class='text-danger'>{contador['vencidos']} vencido(s)</strong>")
    
    if contador["hoje"] > 0:
        resumo.append(f"<strong class='text-danger'>{contador['hoje']} vence(m) hoje</strong>")
    
    if contador["7_dias"] > 0:
        resumo.append(f"<strong class='text-warning'>{contador['7_dias']} em 7 dias</strong>")
    
    if contador["30_dias"] > 0:
        resumo.append(f"<strong class='text-info'>{contador['30_dias']} em 30 dias</strong>")
    
    if not resumo:
        return "Sem documentos próximos do vencimento"
    
    return f"Documentos: {', '.join(resumo)}"


def gerar_dados_dashboard() -> Dict[str, Any]:
    """
    Gera dados para o dashboard relacionados a vencimentos.
    
    Returns:
        Dicionário com dados para exibição no dashboard
    """
    contagem = contar_documentos_por_vencimento()
    vencidos, proximos = verificar_documentos_vencimento()
    
    # Preparar alertas urgentes
    alertas_urgentes = []
    
    # Adicionar documentos vencidos aos alertas
    for doc in vencidos[:5]:  # Limitar a 5 para não sobrecarregar
        alertas_urgentes.append({
            "tipo": "documento",
            "id": doc.id,
            "titulo": doc.nome if hasattr(doc, "nome") else "Documento",
            "status": "vencido",
            "dias": calcular_dias_restantes(doc.data_vencimento),
            "data": doc.data_vencimento.strftime("%d/%m/%Y") if doc.data_vencimento else "N/A",
            "link": f"/admin/documento/{doc.id}"
        })
    
    # Adicionar documentos próximos do vencimento (7 dias)
    for doc in proximos:
        dias = calcular_dias_restantes(doc.data_vencimento)
        if dias <= 7:
            alertas_urgentes.append({
                "tipo": "documento",
                "id": doc.id,
                "titulo": doc.nome if hasattr(doc, "nome") else "Documento",
                "status": "proximo",
                "dias": dias,
                "data": doc.data_vencimento.strftime("%d/%m/%Y") if doc.data_vencimento else "N/A",
                "link": f"/admin/documento/{doc.id}"
            })
    
    # Ordenar alertas por urgência (vencidos primeiro, depois por dias restantes)
    alertas_urgentes.sort(key=lambda x: (x["dias"] >= 0, x["dias"]))
    
    return {
        "contagem": contagem,
        "resumo": formatar_resumo_vencimentos(contagem),
        "alertas_urgentes": alertas_urgentes[:10],  # Limitar a 10 alertas
        "total_alertas": len(vencidos) + len(proximos)
    }


# Exportar funções principais
__all__ = [
    'verificar_documentos_vencimento',
    'gerar_alertas_vencimento',
    'agrupar_documentos_por_prazo',
    'contar_documentos_por_vencimento',
    'formatar_resumo_vencimentos',
    'gerar_dados_dashboard'
]