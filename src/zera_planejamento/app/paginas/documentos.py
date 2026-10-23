"""Importação livre: qualquer planilha (Excel, CSV) ou PDF com texto → base mensal, com mapa de rótulos por cliente."""
import datetime as dt

import pandas as pd
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import base_do, exigir_cliente, tabela_brl
from zera_planejamento.base import COLUNAS
from zera_planejamento.dominio.generico import (EXTENSOES, IGNORAR, ErroLeituraDocumento, destinos, detectar_layout,
                                                extrair, lembrar, ler_tabelas, montar_parcial)
from zera_planejamento.formatos import brl, comp

c = exigir_cliente()
v.cabecalho("Importar outros documentos", f"Cliente · {c.nome}",
            "Qualquer planilha (Excel, CSV) ou PDF com texto: DRE, balancete, faturamento, folha, extratos.")
st.markdown("Envie o documento, confira **a que item da base cada linha corresponde** e grave. O sistema lembra as "
            "suas escolhas para este cliente: na próxima vez, os mesmos rótulos já vêm ligados. Para os relatórios "
            "padrão do Domínio, use **Importar Domínio**.")

ROTULO_COLUNA = {k: d for k, (_, d) in COLUNAS.items()}
OPCOES = ["Ignorar"] + list(ROTULO_COLUNA.values())
PARA_CHAVE = {"Ignorar": IGNORAR, **{d: k for k, d in ROTULO_COLUNA.items()}}

class _Arquivo:
    """Arquivo local com a mesma interface do upload (usado pelos testes automáticos da tela)."""
    def __init__(self, caminho):
        self.name, self._dados = caminho.name, caminho.read_bytes()

    def getbuffer(self):
        return memoryview(self._dados)


arquivos = st.file_uploader("Documentos", type=[e.strip(".") for e in EXTENSOES], accept_multiple_files=True)
arquivos = arquivos or [_Arquivo(p) for p in st.session_state.get("_documentos_teste", [])]
if not arquivos:
    st.stop()
arq = arquivos[0] if len(arquivos) == 1 else st.selectbox("Documento", arquivos, format_func=lambda a: a.name)

pendentes = c.pasta() / "importacoes" / "pendentes"
pendentes.mkdir(parents=True, exist_ok=True)
caminho = pendentes / arq.name
caminho.write_bytes(arq.getbuffer())
try:
    tabelas = ler_tabelas(caminho)
except ErroLeituraDocumento as erro:
    st.error(str(erro), icon=":material/error:")
    st.stop()

# a tabela com mais valores aproveitáveis vem selecionada
aproveitavel = [len(extrair(t, detectar_layout(t), pd.Period(dt.date.today(), "M"))) for t in tabelas]
i_padrao = max(range(len(tabelas)), key=lambda i: aproveitavel[i])
v.rotulo("1 · Tabela encontrada")
idx = st.selectbox("Tabela", range(len(tabelas)), index=i_padrao,
                   format_func=lambda i: f"{tabelas[i].origem} — {tabelas[i].tamanho} — {aproveitavel[i]} valores")
tab = tabelas[idx]
with st.expander("Ver a tabela como foi lida"):
    st.dataframe(pd.DataFrame(tab.linhas).astype(str).replace({"None": ""}), width="stretch", hide_index=True)

layout = detectar_layout(tab)
st.info(f"Leitura: **{layout.descricao()}**.", icon=":material/table_chart:")
competencia_unica = None
a, b = st.columns(2)
if layout.tipo == "unico":
    hoje = pd.Period(dt.date.today(), "M")
    opcoes = list(pd.period_range(hoje - 36, hoje, freq="M"))[::-1]
    sugerida = layout.competencia_sugerida
    indice = opcoes.index(sugerida) if sugerida in opcoes else 1
    competencia_unica = a.selectbox("Competência do documento", opcoes, index=indice, format_func=comp,
                                    help="O documento não traz os meses em colunas: informe a que mês os valores se "
                                         "referem." + (" Sugestão tirada da data no título." if sugerida else ""))
    if layout.talvez_acumulado:
        st.warning("O título indica valores **acumulados no exercício** (vários meses somados). Gravar num único mês "
                   "distorce a análise mês a mês: prefira a DRE mês a mês ou, se for relatório do Domínio, use "
                   "**Importar Domínio**, que separa os meses.", icon=":material/warning:")
acumulado = b.checkbox("Valores acumulados no ano", value=False,
                       help="Marque se cada mês traz o acumulado desde janeiro (DRE/balancete acumulados): o sistema "
                            "calcula o valor de cada mês pela diferença.")
longo = extrair(tab, layout, competencia_unica)
if longo.empty:
    st.warning("Não encontrei linhas com rótulo e valor nesta tabela. Escolha outra tabela acima ou envie o documento "
               "em Excel.", icon=":material/warning:")
    st.stop()

# ---------------- mapa de rótulos ----------------
v.rotulo("2 · A que item da base cada linha corresponde")
resumo = longo.groupby("rotulo", sort=False).agg(total=("valor", lambda s: s.abs().sum()), meses=("competencia", "nunique"))
escolha = destinos(c.mapa_rotulos, resumo.index, c.coluna_servico)
editor = pd.DataFrame({
    "Rótulo no documento": resumo.index,
    "Total no documento": resumo["total"].map(brl).values,
    "Meses": resumo["meses"].values,
    "Vai para": [("Ignorar" if escolha[r][0] == IGNORAR else ROTULO_COLUNA[escolha[r][0]]) for r in resumo.index],
    "Escolha": ["salva para este cliente" if escolha[r][1] == "salvo" else "sugestão — confira" for r in resumo.index],
})
editado = st.data_editor(
    editor, hide_index=True, width="stretch", key=f"mapa_{arq.name}_{idx}",
    disabled=["Rótulo no documento", "Total no documento", "Meses", "Escolha"],
    column_config={"Vai para": st.column_config.SelectboxColumn("Vai para", options=OPCOES, required=True, width="large")})
st.caption("Totais, subtotais e o lucro devem ficar em **Ignorar** para não somar em dobro. Linhas ligadas ao mesmo "
           "item são somadas. Os valores entram positivos (a base guarda receitas, custos e despesas sem sinal).")
destino_por_rotulo = {r: PARA_CHAVE[x] for r, x in zip(editado["Rótulo no documento"], editado["Vai para"])}

# ---------------- prévia ----------------
parcial = montar_parcial(longo, destino_por_rotulo, acumulado)
v.rotulo("3 · O que será gravado")
if parcial.empty:
    st.info("Nenhuma linha ligada a um item da base ainda.")
    st.stop()
previa = parcial.T
previa.index = [ROTULO_COLUNA[i] for i in previa.index]
previa.columns = [comp(p) for p in previa.columns]
st.dataframe(tabela_brl(previa), width="stretch")
base = base_do(c)
existentes = [(p, col) for p in parcial.index for col in parcial.columns
              if p in base.dados.index and pd.notna(base.dados.at[p, col]) and pd.notna(parcial.at[p, col])]
if existentes:
    st.warning(f"{len(existentes)} valor(es) já existem na base e serão substituídos por este documento.",
               icon=":material/sync_problem:")

if st.button("Gravar na base do cliente", type="primary", icon=":material/save:"):
    pasta = c.pasta() / "importacoes" / f"{dt.datetime.now():%Y%m%d-%H%M%S}"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / arq.name).write_bytes(caminho.read_bytes())
    n = len(base.mesclar(parcial, f"documento {arq.name}"))
    base.salvar(c.pasta())
    c.mapa_rotulos = lembrar(c.mapa_rotulos, destino_por_rotulo)
    c.salvar()
    caminho.unlink(missing_ok=True)
    st.success(f"{n} valores gravados. O documento original ficou guardado em {pasta}; as escolhas de rótulo foram "
               "salvas para este cliente.", icon=":material/check:")
    a, b = st.columns(2)
    a.page_link("paginas/dashboard.py", label="Ver o dashboard do cliente", icon=":material/dashboard:")
    b.page_link("paginas/base.py", label="Conferir a base mensal", icon=":material/table_view:")
