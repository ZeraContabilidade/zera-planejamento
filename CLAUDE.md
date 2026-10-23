# CLAUDE.md — instruções para o Claude Code neste repositório

Leia o `PROMPT.md` (especificação, decisões e roadmap) antes de qualquer mudança. Outros agentes (Codex) trabalham em paralelo conforme `AGENTS.md`: respeite a divisão de arquivos da seção 9 de lá.

## Comandos
- Instalar (dev): `python -m pip install -e .[dev]`
- Testes: `python -m pytest` (os de `amostras/` são pulados se a pasta não existir)
- App: `zera-planejamento app` (ou `python -m zera_planejamento app`)
- Lote: `zera-planejamento importar --cliente <cnpj8> arquivos...` / `zera-planejamento relatorio --cliente <cnpj8>`

## Convenções
- Código, nomes e mensagens em português. Valores em R$ com `formatos.brl`/`formatos.pct` (nunca `:.2%` com `replace`).
- Regras tributárias só em `regras/` (ou `regras/dados/*.csv`), com base legal no docstring. Incerteza → `[CONFERIR]` + `regras.pendencias_conferir()`.
- O motor (`calculo/`) é a fonte única dos números. Relatórios e telas só exibem.
- Base mensal: colunas canônicas em `base.COLUNAS`. Nova coluna = atualizar `COLUNAS`, De-Para, projeção (`VARIAVEIS`/`FIXOS`) e testes.
- Toda regra de cálculo nova tem teste com memória de cálculo em comentário. A regressão da CS Geartech (`tests/test_regressao_cs_geartech.py`) precisa passar ou a diferença ser explicada.
- **Nunca** versionar dados de cliente (`amostras/`, `dados/`, `.xls`, `.xlsx`, `.pdf` já estão no `.gitignore`).
- Streamlit: páginas em `app/paginas/`, caminhos relativos a `app/main.py`; usar `width="stretch"`.
- Ao terminar: dizer o que mudou, como testou e o próximo passo.
