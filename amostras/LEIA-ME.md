# amostras/

Relatórios reais do Domínio para testes locais. **Esta pasta não vai para o GitHub**: tem dados de cliente.

Estrutura esperada para o teste de regressão (`tests/test_regressao_cs_geartech.py`):

```
amostras/cs_geartech/
    Servicos.xls        # Acompanhamento de Serviços 01/01/2026 a 30/09/2026
    Entradas.xls        # Acompanhamento de Entradas 01/01/2026 a 30/09/2026
    Folha.xls           # Extrato Mensal jan–set/2026
    DRE.xls             # D.R.E. em 30/09/2026 (acumulada)
```

Sem esses arquivos, os testes marcados como `amostras` são pulados.
