"""Plugin optativo de pytest para executar sem acesso ao Drive do escritório.

Uso: PYTHONPATH=src;tests python -m pytest -p ambiente_sintetico
Só desativa a descoberta automática de identidade visual em pastas externas.
O PDF continua sendo gerado e as páginas Streamlit continuam sendo executadas.
"""
import pytest


@pytest.fixture(autouse=True)
def identidade_visual_sem_drive(monkeypatch):
    from zera_planejamento import configuracoes
    monkeypatch.setattr(configuracoes, 'CANDIDATOS_KIT', [])
