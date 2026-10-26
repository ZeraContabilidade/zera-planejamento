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
@keyframes zera-entra {{ from {{ transform: translateY(6px); }} to {{ transform: none; }} }}
@keyframes zera-brilho {{ from {{ background-position: 200% 0; }} to {{ background-position: -200% 0; }} }}
.zera-cab {{ position: relative; display: flex; align-items: center; min-height: 128px; margin: -0.6rem 0 1.5rem;
  background: {PRETO}; border-radius: 10px; overflow: hidden; animation: zera-entra .45s ease-out both;
  box-shadow: 0 10px 30px -18px rgba(17,17,17,.55); }}
.zera-cab::before {{ content: ""; position: absolute; inset: 0 0 0 52%;
  background: repeating-linear-gradient(115deg, transparent 0 22px, rgba(197,161,95,.10) 22px 23px);
  mask-image: linear-gradient(90deg, transparent, #000 40%); -webkit-mask-image: linear-gradient(90deg, transparent, #000 40%); }}
.zera-cab::after {{ content: ""; position: absolute; top: 0; bottom: 0; right: 150px; width: 34px; background: {DOURADO};
  transform: skewX(-24deg); opacity: .95; }}
.zera-cab .txt {{ flex: 1; padding: 20px 26px 22px; z-index: 1; }}
.zera-cab .rot {{ font-family: Inter, sans-serif; font-size: .66rem; letter-spacing: .24em; text-transform: uppercase;
  color: {DOURADO}; font-weight: 700; }}
.zera-cab .tit {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 2.4rem; font-weight: 700;
  color: #F6F0E2; line-height: 1.05; margin: 6px 0 6px; }}
.zera-cab .sub {{ font-size: .82rem; color: #B9AF9C; max-width: 62ch; }}
.zera-cab .marca {{ position: relative; width: 150px; flex: none; align-self: stretch; z-index: 1; }}
.zera-cab .marca img {{ position: absolute; right: 18px; top: 50%; transform: translateY(-50%); width: 96px; }}
.zera-cab .fio {{ position: absolute; left: 26px; right: 26px; bottom: 0; height: 2px;
  background: linear-gradient(90deg, {DOURADO}, rgba(197,161,95,0) 70%); }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{ box-shadow: inset 3px 0 0 {DOURADO}; }}
[data-testid="stSidebarNavLink"]:hover {{ box-shadow: inset 3px 0 0 rgba(197,161,95,.5); }}
.zera-ola {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.55rem; color: {PRETO}; margin: .2rem 0 .1rem; }}
.zera-ola small {{ display: block; font-family: Inter, sans-serif; font-size: .78rem; color: {CINZA}; letter-spacing: .02em; }}
.zera-anel {{ --p: 0; width: 54px; height: 54px; border-radius: 50%; flex: none; display: grid; place-items: center;
  background: conic-gradient({DOURADO} calc(var(--p) * 1%), #ECE5D6 0); }}
.zera-anel span {{ width: 42px; height: 42px; border-radius: 50%; background: #fff; display: grid; place-items: center;
  font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 700; font-size: 1rem; color: {PRETO}; }}
.zera-cliente {{ display: flex; gap: 14px; align-items: center; padding: 4px 2px 8px; }}
.zera-cliente .n {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.22rem; font-weight: 700; color: {PRETO};
  line-height: 1.1; }}
.zera-cliente .m {{ font-size: .74rem; color: {CINZA}; margin-top: 2px; }}
.zera-tag {{ display: inline-block; font-size: .62rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
  padding: 2px 7px; border-radius: 3px; background: {CREME}; color: {DOURADO_TXT}; margin-right: 4px; }}
.zera-tag.escura {{ background: {PRETO}; color: {DOURADO}; }}
.zera-chip {{ display: inline-block; font-size: .72rem; font-weight: 700; padding: 2px 8px; border-radius: 99px; }}
.zera-chip.sobe {{ background: #F7E6E9; color: {VINHO}; }} .zera-chip.desce {{ background: #E5F2EA; color: {VERDE}; }}
.zera-chip.igual {{ background: {CREME}; color: {CINZA}; }}
.zera-corrida {{ display: grid; gap: 10px; margin: .3rem 0; }}
.zera-corrida .l {{ display: grid; grid-template-columns: 170px 1fr 120px; gap: 12px; align-items: center; }}
.zera-corrida .nome {{ font-size: .84rem; color: {TEXTO}; }} .zera-corrida .nome b {{ color: {PRETO}; }}
.zera-corrida .trilho {{ position: relative; height: 22px; background: #F3EEE3; border-radius: 4px; overflow: hidden; }}
.zera-corrida .base {{ position: absolute; inset: 0 auto 0 0; border-right: 2px dashed #9B917F; opacity: .9; }}
.zera-corrida .sim {{ position: absolute; inset: 4px auto 4px 0; border-radius: 3px; transition: width .35s ease; }}
.zera-corrida .val {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.1rem; font-weight: 700; text-align: right; }}
.zera-rot {{ display: flex; align-items: center; gap: 12px; margin: 1.6rem 0 .6rem; font-size: .68rem; font-weight: 700;
  letter-spacing: .2em; text-transform: uppercase; color: {DOURADO_TXT}; }}
.zera-rot::after {{ content: ""; flex: 1; height: 1px; background: {BORDA}; }}
.zera-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); gap: 12px; margin: .2rem 0 .4rem; }}
.zera-kpi {{ background: #fff; border: 1px solid {BORDA}; border-top: 3px solid {DOURADO}; border-radius: 8px;
  padding: 12px 14px 10px; transition: transform .18s ease, box-shadow .18s ease; animation: zera-entra .4s ease-out both; }}
.zera-kpi:hover {{ transform: translateY(-3px); box-shadow: 0 12px 24px -16px rgba(168,132,63,.65); }}
.zera-kpi:nth-child(2) {{ animation-delay: .05s; }} .zera-kpi:nth-child(3) {{ animation-delay: .1s; }}
.zera-kpi:nth-child(4) {{ animation-delay: .15s; }} .zera-kpi:nth-child(5) {{ animation-delay: .2s; }}
.zera-kpi:nth-child(6) {{ animation-delay: .25s; }}
.zera-kpi.escuro {{ background: linear-gradient(110deg, {PRETO} 40%, #2a2416 50%, {PRETO} 60%) ; background-size: 300% 100%;
  animation: zera-entra .4s ease-out both, zera-brilho 2.4s ease-out .5s 1; }}
.zera-kpi.escuro {{ border-color: {PRETO}; border-top-color: {DOURADO}; }}
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
      <div class="marca"><img src="/app/static/logo_zera.png" alt="Zera Contabilidade"></div>
      <div class="fio"></div></div>""")


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


def saudacao(nome: str, linha: str) -> None:
    hora = __import__("datetime").datetime.now().hour
    ola = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")
    st.html(f'<div class="zera-ola">{ola}, {_e(nome)}.<small>{_e(linha)}</small></div>')


def cartao_cliente(nome: str, meta: str, progresso: float, tags: list[tuple[str, bool]]) -> None:
    """Cartão de cliente com anel de progresso do roteiro (0–1) e etiquetas (texto, escura)."""
    p = max(0, min(100, round(progresso * 100)))
    etiquetas = "".join(f'<span class="zera-tag{" escura" if escura else ""}">{_e(t)}</span>' for t, escura in tags)
    st.html(f'<div class="zera-cliente"><div class="zera-anel" style="--p:{p}"><span>{p}%</span></div>'
            f'<div><div class="n">{_e(nome)}</div><div class="m">{_e(meta)}</div><div style="margin-top:6px">'
            f'{etiquetas}</div></div></div>')


def chip(delta: float, texto: str, bom_se_cair: bool = True) -> str:
    """Etiqueta de variação: verde quando o movimento é bom (por padrão, imposto caindo)."""
    if abs(delta) < 0.005:
        classe = "igual"
    else:
        classe = "desce" if (delta < 0) == bom_se_cair else "sobe"
    return f'<span class="zera-chip {classe}">{_e(texto)}</span>'


def corrida(linhas: list[dict]) -> None:
    """Barras de comparação base × simulado. Cada linha: nome, base, sim, cor, destaque (bool), valor (texto), chip."""
    maximo = max([max(l["base"], l["sim"]) for l in linhas] + [1.0])
    itens = "".join(
        f'<div class="l"><div class="nome">{"<b>" if l.get("destaque") else ""}{_e(l["nome"])}'
        f'{"</b>" if l.get("destaque") else ""}<div>{l.get("chip", "")}</div></div>'
        f'<div class="trilho"><div class="base" style="width:{l["base"] / maximo * 100:.1f}%"></div>'
        f'<div class="sim" style="width:{l["sim"] / maximo * 100:.1f}%;background:{l["cor"]}"></div></div>'
        f'<div class="val">{_e(l["valor"])}</div></div>' for l in linhas)
    st.html(f'<div class="zera-corrida">{itens}</div>')


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
