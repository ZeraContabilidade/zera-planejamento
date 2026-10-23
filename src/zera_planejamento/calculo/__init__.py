"""Motor de cálculo único (fonte oficial dos números do sistema)."""
from .motor import COMPONENTES, NOME_TRIBUTO, REGIMES, ROTULO, Resultado, calcular, simular_transicao

__all__ = ["calcular", "simular_transicao", "Resultado", "REGIMES", "ROTULO", "COMPONENTES", "NOME_TRIBUTO"]
