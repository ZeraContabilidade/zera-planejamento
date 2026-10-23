"""
Identidade visual Zera no app: CSS, cabeçalho com a diagonal dourada, cartões de indicador,
faixa de recomendação, rótulos de seção e estilo dos gráficos Altair.

Paleta e fontes do kit "ZERA - IDENTIDADE VISUAL": preto #111111, dourado #C5A15F (fios) e #A8843F
(texto), texto #1A1A1A, cinza #5F5F5F; Cormorant Garamond nos títulos e números, Inter no texto.
O tema base (cores, fontes, barra lateral preta) está em ``app/.streamlit/config.toml``.
"""
from __future__ import annotations

import html
from pathlib import Path

import altair as alt
import streamlit as st

PRETO, DOURADO, DOURADO_TXT, TEXTO, CINZA = "#111111", "#C5A15F", "#A8843F", "#1A1A1A", "#5F5F5F"
CREME, BORDA, VERDE, VINHO = "#F7F3EA", "#E8E1D3", "#2E7D4F", "#A23E55"
ESTATICO = Path(__file__).parent / "static"
LOGO = ESTATICO / "logo_zera.png"

CSS = f"""
<style>
h1, h2, h3, .zera-serif {{ font-family: 'Cormorant Garamond', Georgia, serif !important; letter-spacing: .01em; }}
h1 {{ font-weight: 700 !important; }}
h2, h3 {{ font-weight: 700 !important; color: {PRETO}; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] {{ border-color: #2E2E2E; }}
[data-testid="stSidebarNavItems"] [data-testid="stNavSectionHeader"] {{
  color: {DOURADO}; text-transform: uppercase; letter-spacing: .16em; font-size: .68rem; }}
[data-testid="stMetricValue"] {{ font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 700; }}
.zera-cab {{ position: relative; display: flex; align-items: stretch; min-height: 104px; margin: -0.5rem 0 1.4rem;
  border-bottom: 1px solid {DOURADO}; overflow: hidden; }}
.zera-cab .txt {{ flex: 1; padding: 6px 0 14px; z-index: 1; }}
.zera-cab .rot {{ font-family: Inter, sans-serif; font-size: .68rem; letter-spacing: .2em; text-transform: uppercase;
  color: {DOURADO_TXT}; font-weight: 700; }}
.zera-cab .tit {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 2.35rem; font-weight: 700;
  color: {PRETO}; line-height: 1.05; margin: 4px 0 6px; }}
.zera-cab .sub {{ font-size: .82rem; color: {CINZA}; }}
.zera-cab .marca {{ position: relative; width: 230px; flex: none; }}
.zera-cab .marca::before {{ content: ""; position: absolute; inset: 0 0 0 26px; background: {DOURADO};
  clip-path: polygon(42% 0, 52% 0, 22% 100%, 12% 100%); }}
.zera-cab .marca::after {{ content: ""; position: absolute; inset: 0; background: {PRETO};
  clip-path: polygon(56% 0, 100% 0, 100% 100%, 36% 100%); }}
.zera-cab .marca img {{ position: absolute; right: 16px; top: 50%; transform: translateY(-50%); width: 92px; z-index: 2; }}
.zera-rot {{ display: flex; align-items: center; gap: 12px; margin: 1.6rem 0 .6rem; font-size: .68rem; font-weight: 700;
  letter-spacing: .2em; text-transform: uppercase; color: {DOURADO_TXT}; }}
.zera-rot::after {{ content: ""; flex: 1; height: 1px; background: {BORDA}; }}
.zera-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); gap: 12px; margin: .2rem 0 .4rem; }}
.zera-kpi {{ background: #fff; border: 1px solid {BORDA}; border-top: 3px solid {DOURADO}; border-radius: 6px;
  padding: 12px 14px 10px; }}
.zera-kpi.escuro {{ background: {PRETO}; border-color: {PRETO}; border-top-color: {DOURADO}; }}
.zera-kpi .l {{ font-size: .66rem; letter-spacing: .14em; text-transform: uppercase; color: {CINZA}; font-weight: 700; }}
.zera-kpi.escuro .l {{ color: {DOURADO}; }}
.zera-kpi .v {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.65rem; font-weight: 700; color: {PRETO};
  line-height: 1.1; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.zera-kpi.escuro .v {{ color: #F4EDDD; }}
.zera-kpi .d {{ font-size: .74rem; color: {CINZA}; margin-top: 2px; }}
.zera-kpi.escuro .d {{ color: #BDB3A0; }}
.zera-kpi .d .pos {{ color: {VERDE}; font-weight: 700; }}
.zera-kpi .d .neg {{ color: {VINHO}; font-weight: 700; }}
.zera-kpi.escuro .d .pos {{ color: #8FD1A8; }}
.zera-faixa {{ display: flex; gap: 18px; align-items: center; background: {PRETO}; color: #EDE6D6; border-left: 4px solid
  {DOURADO}; border-radius: 6px; padding: 16px 20px; margin: .6rem 0 .4rem; }}
.zera-faixa .t {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.45rem; font-weight: 700; color: #F4EDDD; }}
.zera-faixa .x {{ font-size: .86rem; color: #CFC6B3; margin-top: 2px; }}
.zera-faixa .selo {{ flex: none; font-size: .66rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
  color: {PRETO}; background: {DOURADO}; border-radius: 3px; padding: 6px 10px; }}
.zera-prazo {{ display: grid; grid-template-columns: 92px 1fr; gap: 10px; padding: 9px 0; border-bottom: 1px solid {BORDA}; }}
.zera-prazo .dt {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.25rem; font-weight: 700; color: {PRETO}; }}
.zera-prazo .dd {{ font-size: .7rem; color: {CINZA}; }}
.zera-prazo .ev {{ font-size: .84rem; color: {TEXTO}; }}
.zera-prazo .ac {{ display: inline-block; font-size: .62rem; font-weight: 700; letter-spacing: .12em; padding: 2px 6px;
  border-radius: 3px; margin-right: 6px; background: {CREME}; color: {DOURADO_TXT}; }}
.zera-prazo .ac.DECIDIR {{ background: {PRETO}; color: {DOURADO}; }}
.zera-selo {{ display: inline-block; font-size: .7rem; font-weight: 700; padding: 3px 9px; border-radius: 99px;
  margin-right: 6px; }}
.zera-rodape {{ margin-top: 2.4rem; padding-top: 8px; border-top: 1px solid {DOURADO}; font-size: .66rem;
  letter-spacing: .18em; text-transform: uppercase; color: {CINZA}; display: flex; justify-content: space-between; }}
</style>
"""


def _e(texto) -> str:
    return html.escape(str(texto))


def aplicar_identidade() -> None:
    """CSS da Zera e logo na barra lateral. Chamar uma vez no ``main.py``."""
    st.html(CSS)
    if LOGO.exists():
        st.logo(str(LOGO), size="large")


def cabecalho(titulo: str, rotulo: str = "", subtitulo: str = "") -> None:
    """Título da página no padrão do timbrado: rótulo dourado, título em Cormorant e a diagonal com a logo."""
    st.html(f"""<div class="zera-cab"><div class="txt"><div class="rot">{_e(rotulo)}</div>
      <div class="tit">{_e(titulo)}</div><div class="sub">{_e(subtitulo)}</div></div>
      <div class="marca"><img src="/app/static/logo_zera.png" alt="Zera Contabilidade"></div></div>""")


def rotulo(texto: str) -> None:
    st.html(f'<div class="zera-rot">{_e(texto)}</div>')


def kpis(cartoes: list[dict]) -> None:
    """Cartões de indicador. Cada um: {"l": rótulo, "v": valor, "d": detalhe (HTML simples), "escuro": bool}."""
    itens = "".join(
        f'<div class="zera-kpi{" escuro" if c.get("escuro") else ""}"><div class="l">{_e(c["l"])}</div>'
        f'<div class="v" title="{_e(c["v"])}">{_e(c["v"])}</div><div class="d">{c.get("d", "")}</div></div>'
        for c in cartoes)
    st.html(f'<div class="zera-kpis">{itens}</div>')


def variacao(valor: float, texto: str, bom_se_positivo: bool = True) -> str:
    """Trecho colorido para o detalhe do cartão (▲ verde quando bom, ▼ vinho quando ruim)."""
    if valor != valor or valor == 0:          # NaN ou zero
        return _e(texto)
    bom = (valor > 0) == bom_se_positivo
    seta = "▲" if valor > 0 else "▼"
    return f'<span class="{"pos" if bom else "neg"}">{seta} {_e(texto)}</span>'


def faixa(titulo: str, texto: str, selo: str = "") -> None:
    selo_html = f'<div class="selo">{_e(selo)}</div>' if selo else ""
    st.html(f'<div class="zera-faixa">{selo_html}<div><div class="t">{_e(titulo)}</div>'
            f'<div class="x">{_e(texto)}</div></div></div>')


def prazos_html(linhas: list[tuple[str, str, str, str]]) -> None:
    """Linhas (data dd/mm/aaaa, "em N dias", ação, evento)."""
    itens = "".join(f'<div class="zera-prazo"><div><div class="dt">{_e(d)}</div><div class="dd">{_e(dd)}</div></div>'
                    f'<div class="ev"><span class="ac {_e(a)}">{_e(a)}</span>{_e(ev)}</div></div>'
                    for d, dd, a, ev in linhas)
    st.html(f"<div>{itens}</div>")


def rodape(texto: str = "Rascunho técnico — revisar antes de enviar ao cliente") -> None:
    st.html(f'<div class="zera-rodape"><span>Zera Assessoria Empresarial e Contábil</span><span>{_e(texto)}</span></div>')


def grafico(chart: alt.TopLevelMixin, altura: int = 300) -> alt.TopLevelMixin:
    """Aplica o estilo Zera a um gráfico Altair (fontes, eixos discretos, legenda no topo)."""
    return (chart.properties(height=altura)
            .configure(font="Inter", background="transparent")
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=CINZA, titleColor=CINZA, labelFontSize=11, titleFontSize=11, gridColor="#EFEAE0",
                            domainColor="#D9D1C1", tickColor="#D9D1C1", titleFontWeight="normal")
            .configure_legend(orient="top", labelColor=TEXTO, titleColor=CINZA, labelFontSize=11, titleFontSize=10,
                              symbolType="circle")
            .configure_title(font="Cormorant Garamond", fontSize=18, color=PRETO, anchor="start"))
