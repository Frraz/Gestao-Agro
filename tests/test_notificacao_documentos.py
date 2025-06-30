import pytest
from src.main import create_app
from src.utils.tasks_notificacao import processar_notificacoes_documentos

@pytest.fixture
def app():
    app = create_app({"TESTING": True})
    with app.app_context():
        yield app

def test_processar_notificacoes_documentos(app):
    enviados = processar_notificacoes_documentos()
    # Aqui pode ser assert enviado == 0, ou simplesmente garantir que não levanta erro
    assert isinstance(enviados, int)
    assert enviados >= 0