import datetime
from flask import current_app, flash
from src.models.documento import Documento

def verificar_documentos_vencimento():
    """
    Verifica documentos vencidos ou próximos do vencimento.
    Esta função é chamada quando o usuário acessa o dashboard ou a página de vencimentos.
    
    Retorna:
        tuple: (documentos_vencidos, documentos_proximos_vencimento)
    """
    try:
        # Buscar documentos com data de vencimento
        documentos = Documento.query.filter(Documento.data_vencimento.isnot(None)).all()
        
        # Separar documentos vencidos e próximos do vencimento
        documentos_vencidos = []
        documentos_proximos = []
        
        for documento in documentos:
            if documento.esta_vencido:
                documentos_vencidos.append(documento)
            elif documento.precisa_notificar:
                documentos_proximos.append(documento)
        
        return documentos_vencidos, documentos_proximos
        
    except Exception as e:
        current_app.logger.error(f"Erro ao verificar documentos vencidos: {str(e)}")
        return [], []

def gerar_alertas_vencimento():
    """
    Gera alertas para exibição na interface sobre documentos vencidos ou próximos do vencimento.
    """
    documentos_vencidos, documentos_proximos = verificar_documentos_vencimento()
    
    # Gerar alertas para documentos vencidos
    if documentos_vencidos:
        flash(
            f'Atenção! Existem {len(documentos_vencidos)} documento(s) vencido(s). '
            f'<a href="/admin/documentos/vencidos">Verificar agora</a>', 
            'danger'
        )
    
    # Gerar alertas para documentos próximos do vencimento
    if documentos_proximos:
        flash(
            f'Existem {len(documentos_proximos)} documento(s) próximo(s) do vencimento. '
            f'<a href="/admin/documentos/vencidos">Verificar agora</a>', 
            'warning'
        )
    
    return documentos_vencidos, documentos_proximos
