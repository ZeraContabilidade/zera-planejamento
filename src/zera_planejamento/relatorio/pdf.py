"""
Relatório técnico em PDF (ReportLab) com a identidade visual da Zera.

Com o kit "ZERA - IDENTIDADE VISUAL" configurado: timbrado (header_a4.png) no topo de todas as
páginas, Cormorant Garamond nos títulos, Inter no corpo, preto #111111 e dourado #C5A15F, rodapé
"ZERA ASSESSORIA EMPRESARIAL E CONTÁBIL" e página X / N. Sem o kit: mesma estrutura com fontes
padrão e o rodapé de rascunho.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..calculo import COMPONENTES, NOME_TRIBUTO, ROTULO
from ..configuracoes import Configuracoes
from ..formatos import brl, comp, pct
from ..projecao import CENARIOS

PRETO, DOURADO, DOURADO_TXT = colors.HexColor("#111111"), colors.HexColor("#C5A15F"), colors.HexColor("#A8843F")
TEXTO, CINZA, CLARO, LINHA = colors.HexColor("#1A1A1A"), colors.HexColor("#5F5F5F"), colors.HexColor("#F6F0E4"), \
    colors.HexColor("#DDDDDD")
FONTES = {"titulo": "Times-Bold", "corpo": "Helvetica", "negrito": "Helvetica-Bold"}

FORA_DO_MODELO = [
    "ICMS-ST, produtos monofásicos e segregação de receitas no PGDAS-D; IPI e Imposto Seletivo; benefícios estaduais "
    "e municipais; ISS fixo de sociedade uniprofissional; desoneração da folha; JCP e incentivos do Lucro Real.",
    "Crédito de PIS/Cofins sobre depreciação do imobilizado (no Lucro Real) e retenções na fonte compensáveis.",
    "Lei 15.270/2025: só entra na conclusão quando os sócios estão cadastrados (seção Sócios + empresa); "
    "rendimentos de outras fontes dependem do que foi informado.",
    "A opção de regime é anual e irretratável (Simples até o último dia útil de janeiro; Presumido/Real com o "
    "primeiro pagamento do ano); a opção semestral pelo IBS/CBS no Simples segue o calendário do CGSN.",
]


def _registrar_fontes(kit: Path | None) -> bool:
    if not kit or not (kit / "fonts").exists():
        return False
    arquivos = {p.name.lower(): p for p in (kit / "fonts").rglob("*.ttf")}

    def achar(*partes):
        return next((p for n, p in arquivos.items() if all(x in n for x in partes)), None)

    corm, inter, inter_b = achar("cormorant", "bold") or achar("cormorant"), achar("inter", "regular") or \
        achar("inter"), achar("inter", "bold")
    if not (corm and inter and inter_b):
        return False
    pdfmetrics.registerFont(TTFont("Cormorant-Bold", str(corm)))
    pdfmetrics.registerFont(TTFont("Inter", str(inter)))
    pdfmetrics.registerFont(TTFont("Inter-Bold", str(inter_b)))
    FONTES.update({"titulo": "Cormorant-Bold", "corpo": "Inter", "negrito": "Inter-Bold"})
    return True


def _estilos():
    f = FONTES
    return {
        "rotulo": ParagraphStyle("r", fontName=f["negrito"], fontSize=7.5, textColor=DOURADO_TXT, leading=10,
                                 spaceBefore=14, spaceAfter=3),
        "titulo": ParagraphStyle("t", fontName=f["titulo"], fontSize=24, leading=28, textColor=PRETO, spaceAfter=6),
        "h2": ParagraphStyle("h", fontName=f["titulo"], fontSize=15, leading=19, textColor=PRETO, spaceAfter=6),
        "corpo": ParagraphStyle("c", fontName=f["corpo"], fontSize=9.5, leading=13.5, textColor=TEXTO, spaceAfter=6),
        "meta": ParagraphStyle("m", fontName=f["corpo"], fontSize=8.5, leading=12, textColor=CINZA, spaceAfter=8),
        "cel": ParagraphStyle("cl", fontName=f["corpo"], fontSize=7.8, leading=10, textColor=TEXTO),
        "celb": ParagraphStyle("cb", fontName=f["negrito"], fontSize=7.8, leading=10, textColor=TEXTO),
        "cab": ParagraphStyle("cab", fontName=f["negrito"], fontSize=7.8, leading=10, textColor=PRETO),
        "item": ParagraphStyle("i", fontName=f["corpo"], fontSize=8.8, leading=12, textColor=TEXTO, leftIndent=10,
                               spaceAfter=3),
        "legenda": ParagraphStyle("l", fontName=f["corpo"], fontSize=7.5, leading=10, textColor=CINZA, spaceAfter=10),
    }


def _tabela(linhas, larguras, destaque=(), alinhar_dir_de=1):
    t = Table(linhas, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    est = [("BACKGROUND", (0, 0), (-1, 0), CLARO), ("LINEBELOW", (0, 0), (-1, 0), 1.2, DOURADO),
           ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINHA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
           ("ALIGN", (alinhar_dir_de, 1), (-1, -1), "RIGHT")]
    est += [("BACKGROUND", (0, i), (-1, i), CLARO) for i in destaque]
    t.setStyle(TableStyle(est))
    return t


class _Canvas(rl_canvas.Canvas):
    timbrado: Path | None = None
    rodape: str = ""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._pags = []

    def showPage(self):
        self._pags.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pags)
        for estado in self._pags:
            self.__dict__.update(estado)
            w, h = A4
            if self.timbrado and self.timbrado.exists():
                self.drawImage(str(self.timbrado), 0, h - 2.6 * cm, width=w, height=2.6 * cm,
                               preserveAspectRatio=True, anchor="n", mask="auto")
            else:
                self.setStrokeColor(DOURADO)
                self.setLineWidth(1.2)
                self.line(2 * cm, h - 1.4 * cm, w - 2 * cm, h - 1.4 * cm)
            self.setStrokeColor(DOURADO)
            self.setLineWidth(0.6)
            self.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)
            self.setFont(FONTES["corpo"], 7)
            self.setFillColor(CINZA)
            self.drawString(2 * cm, 1.05 * cm, self.rodape)
            self.drawRightString(w - 2 * cm, 1.05 * cm, f"{self._pageNumber} / {total}")
            super().showPage()
        super().save()


def exportar_pdf(pl, caminho: Path, graficos: dict[str, Path]) -> Path:
    cfg = Configuracoes.carregar()
    kit = cfg.kit
    com_kit = _registrar_fontes(kit)
    e = _estilos()
    c = pl.cliente
    timbrado = kit / "header_a4.png" if kit else None
    _Canvas.timbrado = timbrado if timbrado and timbrado.exists() else None
    _Canvas.rodape = cfg.escritorio if com_kit else "Rascunho técnico — revisar antes de enviar ao cliente"
    largura = A4[0] - 4 * cm
    doc = SimpleDocTemplate(str(caminho), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=3.2 * cm if _Canvas.timbrado else 2 * cm, bottomMargin=2 * cm,
                            title=f"Planejamento tributário — {c.nome}", author=cfg.responsavel)
    h, mh, mp = [], pl.meses_historico, pl.meses_projetados

    h += [Paragraph("PLANEJAMENTO TRIBUTÁRIO · PROJEÇÃO SEMESTRAL", e["rotulo"]), Paragraph(c.nome, e["titulo"]),
          Paragraph(f"CNPJ {c.cnpj or '–'} · {c.municipio}/{c.uf} · regime atual: {c.regime_atual} · histórico "
                    f"{comp(mh[0])} a {comp(mh[-1])} · projeção {comp(mp[0])} a {comp(mp[-1])} · emitido em "
                    f"{pl.gerado_em:%d/%m/%Y}", e["meta"])]

    neutro = pl.resumo[pl.resumo.cenario == "Neutro"].set_index("regime")
    validos = neutro[neutro.elegivel].sort_values("tributos")
    m = pl.melhor("Neutro")
    h.append(Paragraph("CONCLUSÃO", e["rotulo"]))
    if m is not None:
        txt = (f"No cenário <b>Neutro</b>, a menor carga nos próximos {len(mp)} meses é no <b>{m['rotulo']}</b>: "
               f"<b>{brl(m['tributos'])}</b> sobre receita de {brl(m['receita'])} — carga efetiva de "
               f"<b>{pct(m['carga'])}</b>.")
        if len(validos) > 1:
            s = validos.iloc[1]
            dif = s["tributos"] - m["tributos"]
            txt += f" O segundo colocado ({s['rotulo']}) custaria {brl(dif)} a mais ({pct(dif / s['tributos'])})."
        h.append(Paragraph(txt, e["corpo"]))
        outros = []
        for nome in ("Otimista", "Pessimista"):
            mm = pl.melhor(nome)
            if mm is not None:
                outros.append(f"{nome}: {mm['rotulo']} ({brl(mm['tributos'])}, {pct(mm['carga'])})")
        h.append(Paragraph("Nos demais cenários, a menor carga fica em — " + "; ".join(outros) + ".", e["corpo"]))

    h += [Paragraph("TABELA RESUMO", e["rotulo"]), Paragraph("Custo do período projetado por cenário e regime", e["h2"])]
    linhas, dest = [[Paragraph(x, e["cab"]) for x in ("Cenário", "Regime", "Receita", "Tributos", "Carga", "Situação")]], []
    for lin in pl.resumo.itertuples():
        st = e["celb"] if lin.melhor else e["cel"]
        if lin.melhor:
            dest.append(len(linhas))
        linhas.append([Paragraph(lin.cenario, st), Paragraph(lin.rotulo, st), Paragraph(brl(lin.receita), st),
                       Paragraph(brl(lin.tributos) if lin.elegivel else "–", st),
                       Paragraph(pct(lin.carga) if lin.elegivel else "–", st),
                       Paragraph("Menor carga" if lin.melhor else ("" if lin.elegivel else "não aplicável"), st)])
    h.append(_tabela(linhas, [2.0 * cm, 4.6 * cm, 2.9 * cm, 2.9 * cm, 1.8 * cm, largura - 14.2 * cm], dest, 2))
    h.append(Paragraph("Simples e Simples híbrido incluem DAS e, quando aplicável, CPP/ICMS/ISS fora do DAS. Presumido e "
                       "Real incluem PIS/Cofins ou CBS/IBS, IRPJ, CSLL, ICMS, ISS e INSS patronal + RAT + Terceiros. "
                       "FGTS fica fora porque é igual em todos.", e["legenda"]))

    h += [Paragraph("BREAK-EVEN TRIBUTÁRIO", e["rotulo"]), Paragraph("Onde um regime passa a valer mais que o outro", e["h2"])]
    linhas = [[Paragraph(x, e["cab"]) for x in ("Comparação", "Equilíbrio", "Projetado", "Leitura")]]
    for q in pl.equilibrio.itertuples():
        f = (lambda v: pct(v, 1)) if q.unidade == "%" else (lambda v: brl(v, 0))
        linhas.append([Paragraph(f"<b>{q.comparacao}</b><br/>{q.indicador}", e["cel"]), Paragraph(f(q.equilibrio), e["cel"]),
                       Paragraph(f(q.projetado), e["cel"]), Paragraph(q.leitura, e["cel"])])
    h.append(_tabela(linhas, [4.4 * cm, 2.2 * cm, 2.2 * cm, largura - 8.8 * cm]))

    def img(p, legenda):
        im = Image(str(p))
        esc = largura / im.imageWidth
        im.drawWidth, im.drawHeight = largura, im.imageHeight * esc
        return KeepTogether([im, Paragraph(legenda, e["legenda"])])

    if pl.socios is not None and not pl.socios.vazia:
        h += [Paragraph("SÓCIOS + EMPRESA", e["rotulo"]),
              Paragraph("Tributos da empresa somados à retirada dos sócios (Lei 15.270/2025)", e["h2"])]
        cab = ("Regime", "Empresa", "Lucros distribuídos", "IRPFM", "INSS + IRRF pró-labore", "Total", "Carga")
        linhas, dest = [[Paragraph(x, e["cab"]) for x in cab]], []
        for lin in pl.socios.resumo.itertuples():
            st = e["celb"] if lin.melhor else e["cel"]
            if lin.melhor:
                dest.append(len(linhas))
            linhas.append([Paragraph(lin.rotulo, st), Paragraph(brl(lin.tributos_pj), st), Paragraph(brl(lin.dividendos), st),
                           Paragraph(brl(lin.irpfm), st), Paragraph(brl(lin.inss_socios + lin.irrf_pro_labore), st),
                           Paragraph(brl(lin.carga_total), st), Paragraph(pct(lin.carga_pct), st)])
        h.append(_tabela(linhas, [4.0 * cm, 2.3 * cm, 2.5 * cm, 2.0 * cm, 2.4 * cm, 2.3 * cm, largura - 15.5 * cm], dest))
        for o in pl.socios.observacoes:
            h.append(Paragraph(o, e["item"], bulletText="•"))
        h.append(Paragraph("IRRF de 10% sobre lucros acima de R$ 50 mil/mês por sócio é antecipação e abate do IRPFM no "
                           "ajuste anual; o custo definitivo considerado é o IRPFM.", e["legenda"]))

    if pl.prazos is not None and not pl.prazos.empty:
        h += [Paragraph("PRAZOS DE DECISÃO", e["rotulo"])]
        linhas = [[Paragraph(x, e["cab"]) for x in ("Data", "Ação", "Evento", "Base legal")]]
        for z in pl.prazos.itertuples():
            st = e["celb"] if z.acao == "DECIDIR" else e["cel"]
            linhas.append([Paragraph(f"{z.data:%d/%m/%Y}", st), Paragraph(z.acao, st), Paragraph(z.evento, e["cel"]),
                           Paragraph(z.base_legal, e["cel"])])
        h.append(_tabela(linhas, [2.2 * cm, 2.2 * cm, largura - 9.4 * cm, 5.0 * cm], alinhar_dir_de=99))

    h += [PageBreak(), Paragraph("GRÁFICOS", e["rotulo"])]
    legendas = {"historico": "Gráfico 1 — Tributos mês a mês no histórico, mesmos dados nos quatro regimes.",
                "cenarios": "Gráfico 2 — Custo do período projetado nos cenários Neutro, Otimista e Pessimista.",
                "margem": "Gráfico 3 — Sensibilidade à margem operacional e pontos de equilíbrio do Lucro Real.",
                "transicao": "Gráfico 4 — Mesmos 12 meses sob as regras de cada ano da transição (2026–2033)."}
    for k, leg in legendas.items():
        if k in graficos:
            h.append(img(graficos[k], leg))

    h.append(Paragraph("COMPOSIÇÃO — CENÁRIO NEUTRO", e["rotulo"]))
    regs = list(neutro.index)
    todos = list(dict.fromkeys(k for r in regs for k in COMPONENTES[r]))
    linhas = [[Paragraph("Tributo", e["cab"])] + [Paragraph(ROTULO[r], e["cab"]) for r in regs]]
    for k in todos:
        vals = [neutro.at[r, f"comp_{k}"] if f"comp_{k}" in neutro.columns and pd.notna(neutro.at[r, f"comp_{k}"])
                and k in COMPONENTES[r] else None for r in regs]
        if all(v in (None, 0) for v in vals):
            continue
        linhas.append([Paragraph(NOME_TRIBUTO[k], e["cel"])] + [Paragraph(brl(v) if v is not None else "", e["cel"]) for v in vals])
    linhas.append([Paragraph("Total", e["celb"])] + [Paragraph(brl(neutro.at[r, "tributos"]), e["celb"]) for r in regs])
    h.append(_tabela(linhas, [4.6 * cm] + [(largura - 4.6 * cm) / len(regs)] * len(regs), [len(linhas) - 1]))

    if pl.transicao is not None and not pl.transicao.empty:
        h += [Paragraph("TRANSIÇÃO DA REFORMA", e["rotulo"]), Paragraph("Últimos 12 meses sob as regras de cada ano", e["h2"])]
        cols = [r for r in pl.transicao.columns if r in ROTULO]
        linhas = [[Paragraph("Ano", e["cab"])] + [Paragraph(ROTULO[r], e["cab"]) for r in cols]]
        for ano, row in pl.transicao.iterrows():
            menor = row[cols].idxmin() if row[cols].notna().any() else None
            linhas.append([Paragraph(str(ano), e["cel"])] + [Paragraph(brl(row[r]) if pd.notna(row[r]) else "–",
                                                                       e["celb"] if r == menor else e["cel"]) for r in cols])
        h.append(_tabela(linhas, [1.6 * cm] + [(largura - 1.6 * cm) / len(cols)] * len(cols)))
        h.append(Paragraph("CBS/IBS de 2027 em diante com alíquotas de referência estimadas (editáveis no cadastro). "
                           "Simples por dentro: o DAS total não muda; muda a partilha.", e["legenda"]))

    h += [PageBreak(), Paragraph("HISTÓRICO MÊS A MÊS", e["rotulo"])]
    mensal = pl.historico.mensal().loc[mh]
    regs_h = list(mensal.columns)
    linhas = [[Paragraph(x, e["cab"]) for x in ["Competência", "Receita"] + [ROTULO[r] for r in regs_h]]]
    rb = pl.base.receita_bruta()
    for per, row in mensal.iterrows():
        menor = row.idxmin() if row.notna().any() else None
        linhas.append([Paragraph(comp(per), e["cel"]), Paragraph(brl(rb[per]), e["cel"])] +
                      [Paragraph(brl(row[r]) if pd.notna(row[r]) else "n/a", e["celb"] if r == menor else e["cel"])
                       for r in regs_h])
    h.append(_tabela(linhas, [2.0 * cm, 2.8 * cm] + [(largura - 4.8 * cm) / len(regs_h)] * len(regs_h)))

    h.append(Paragraph("PREMISSAS E BASE LEGAL", e["rotulo"]))
    rr = c.regras_reforma()
    for t in [
        f"Simples Nacional: LC 123/2006, Anexos I a V; serviços no anexo '{c.anexo_servico}'. RBT12/FS12 dos 12 meses "
        "anteriores até dez/2026 e, a partir de jan/2027, dos 12 meses antecedentes ao mês anterior (LC 214/2025).",
        "Lucro Presumido: presunção por anexo; IRPJ/CSLL trimestrais com adicional; acréscimo de 10% na presunção sobre "
        "a receita acima de R$ 5 mi/ano (LC 224/2025; IN RFB 2.306/2026), IRPJ desde 01/2026 e CSLL desde 04/2026.",
        f"Lucro Real: apuração {c.lr_periodo}; PIS/Cofins não cumulativos com crédito sem ICMS (Lei 14.592/2023); "
        "receitas financeiras 4,65%; compensação de prejuízo limitada a 30%.",
        f"Encargos: INSS 20% sobre salários e pró-labore; RAT {pct(c.rat, 1)} × FAP {str(c.fap).replace('.', ',')}; "
        f"Terceiros {pct(c.terceiros, 1)} sobre salários. ISS {pct(c.iss_aliquota)} no município do cliente.",
        f"Reforma: CBS de referência {pct(rr.cbs_referencia)} (− 0,1 p.p. em 2027–2028), IBS 0,1% em 2027–2028 e "
        f"{pct(rr.ibs_referencia)} de referência a partir de 2029 (10% a 40% até 2032, pleno em 2033); ICMS/ISS reduzidos "
        "10% a 40% de 2029 a 2032 e extintos em 2033. CBS/IBS por fora: preço sem tributos mantido.",
        f"Projeção: {c.projecao.meses} meses; Neutro por {'tendência linear' if c.projecao.metodo == 'tendencia' else 'média'} "
        f"dos últimos {c.projecao.janela} meses; Otimista {pct(c.projecao.otimista, 0)} e Pessimista "
        f"{pct(c.projecao.pessimista, 0)} na receita. Custos e compras acompanham a receita; folha e despesas, não.",
    ]:
        h.append(Paragraph(t, e["item"], bulletText="•"))
    h.append(Paragraph("REGRAS A CONFERIR", e["rotulo"]))
    for t in pl.pendencias:
        h.append(Paragraph(t, e["item"], bulletText="•"))
    h.append(Paragraph("FORA DO MODELO", e["rotulo"]))
    for t in FORA_DO_MODELO:
        h.append(Paragraph(t, e["item"], bulletText="•"))

    al = pl.alertas.como_df()
    if not al.empty:
        h.append(Paragraph("ALERTAS", e["rotulo"]))
        linhas = [[Paragraph(x, e["cab"]) for x in ("Nível", "Origem", "Mensagem")]]
        for a in al.itertuples():
            linhas.append([Paragraph(a.nivel, e["celb"] if a.nivel != "INFO" else e["cel"]), Paragraph(a.origem, e["cel"]),
                           Paragraph(a.mensagem, e["cel"])])
        h.append(_tabela(linhas, [2.0 * cm, 2.4 * cm, largura - 4.4 * cm], alinhar_dir_de=99))
    h += [Spacer(1, 10), Paragraph(f"Simulação com base nos dados informados e na legislação vigente na data de emissão. "
                                   f"Não substitui a apuração oficial. {cfg.responsavel}.", e["legenda"])]
    doc.build(h, canvasmaker=_Canvas)
    return caminho
