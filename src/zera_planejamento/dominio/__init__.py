"""Leitura dos relatórios do Domínio e importação para a base mensal."""
from .depara import DESTINOS, PADRAO, DePara, Regra
from .importar import Importacao, importar_relatorios
from .relatorios import Relatorio, identificar, ler_relatorio

__all__ = ["importar_relatorios", "Importacao", "ler_relatorio", "identificar", "Relatorio", "DePara", "Regra",
           "PADRAO", "DESTINOS"]
