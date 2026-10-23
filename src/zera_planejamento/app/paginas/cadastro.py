"""Cadastro do cliente: premissas que mudam o cálculo."""
import streamlit as st

from zera_planejamento.app import visual as v
from zera_planejamento.app.estado import cliente_atual
from zera_planejamento.cliente import Cliente, Projecao, Socio
from zera_planejamento.consulta_cnpj import ErroConsultaCNPJ, consultar_cnpj

novo = st.session_state.get("novo_cliente", False)     # vale até salvar ou escolher outro cliente na barra lateral
c = None if novo else cliente_atual()
v.cabecalho("Novo cliente" if c is None else c.nome, "Cadastro do cliente", "Premissas do cliente. Tudo aqui muda o cálculo; confira antes de gerar o planejamento.")
c = c or Cliente(nome="")
if st.session_state.pop("cadastro_salvo", False):
    st.success("Cadastro salvo. Próximo passo: importar os relatórios do Domínio.", icon=":material/check:")
    st.page_link("paginas/importar.py", label="Importar relatórios do Domínio", icon=":material/upload_file:")

# ---------------- consulta do CNPJ (dados abertos da Receita Federal) ----------------
v.rotulo("Buscar dados na Receita Federal")
a, b = st.columns([3, 1], vertical_alignment="bottom")
cnpj_busca = a.text_input("CNPJ para consultar", c.cnpj, placeholder="00.000.000/0000-00",
                          help="Preenche razão social, município, UF, atividade (CNAE), regime e sócios.")
if b.button("Buscar na Receita", icon=":material/travel_explore:", width="stretch"):
    try:
        with st.spinner("Consultando o CNPJ..."):
            st.session_state["receita"] = (c.id, consultar_cnpj(cnpj_busca))
    except ErroConsultaCNPJ as erro:
        st.session_state.pop("receita", None)
        st.error(str(erro), icon=":material/error:")
rf = st.session_state.get("receita")
rf = rf[1] if rf and rf[0] == c.id else None
if rf is not None:
    simples = {True: "Optante" + (f" desde {rf.data_opcao_simples}" if rf.data_opcao_simples else ""), False: "Não optante",
               None: "Não informado"}[rf.simples]
    st.markdown(f"#### {rf.razao_social}")
    st.caption(" · ".join(x for x in (rf.cnpj, rf.nome_fantasia, rf.natureza_juridica) if x))
    v.kpis([{"l": "Situação", "v": rf.situacao.title() or "–", "d": f"Aberta em {rf.abertura}" if rf.abertura else "",
             "escuro": True},
            {"l": "Simples Nacional", "v": simples.split(" desde")[0], "d": ("MEI · " if rf.mei else "") + simples},
            {"l": "Última tributação", "v": (rf.ultima_tributacao.split(" (")[0].title() or "–"),
             "d": rf.ultima_tributacao[rf.ultima_tributacao.find("("):] if "(" in rf.ultima_tributacao else "declarada à RFB"},
            {"l": "Município", "v": f"{rf.municipio}/{rf.uf}", "d": rf.porte.title()}])
    socios_txt = ", ".join(f"{s.nome} ({s.qualificacao})" for s in rf.socios[:8]) or "não informado"
    if len(rf.socios) > 8:
        socios_txt += f" e mais {len(rf.socios) - 8}"
    st.caption(f"**Atividade principal:** {rf.atividade}  \n**Sócios no QSA:** {socios_txt}  \n"
               f"Fonte: {rf.fonte}, consultado em {rf.consultado_em}. Os campos abaixo foram preenchidos; confira e salve.")
    if not rf.ativa:
        st.warning(f"Situação cadastral: {rf.situacao}. Confirme com o cliente antes de planejar.", icon=":material/warning:")
    if rf.mei:
        st.info("Empresa optante pelo MEI: o planejamento compara Simples, Presumido e Real, não o SIMEI.",
                icon=":material/info:")
    if rf.cnaes_secundarios:
        with st.expander(f"CNAEs secundários ({len(rf.cnaes_secundarios)})"):
            st.markdown("\n".join(f"- {x}" for x in rf.cnaes_secundarios))

with st.form("cadastro"):
    st.subheader("Identificação")
    a, b, d = st.columns([3, 2, 1])
    nome = a.text_input("Razão social", rf.razao_social if rf else c.nome)
    cnpj = b.text_input("CNPJ", rf.cnpj if rf else c.cnpj)
    uf = d.text_input("UF", rf.uf if rf else c.uf)
    a, b = st.columns(2)
    municipio = a.text_input("Município", rf.municipio if rf else c.municipio)
    atividade = b.text_input("Atividade", rf.atividade if rf else c.atividade)
    socios_qsa = [s for s in rf.socios if s.pessoa_fisica] if rf else []
    importar_socios = False
    if socios_qsa and not c.socios:
        importar_socios = st.checkbox(f"Cadastrar os {len(socios_qsa)} sócio(s) pessoa física do QSA (participação igual; "
                                      "ajuste depois em Sócios e pró-labore)", value=len(socios_qsa) <= 5)

    st.subheader("Enquadramento")
    a, b, d = st.columns(3)
    regimes = ["simples", "presumido", "real"]
    sugerido = rf.regime_sugerido() if rf else None
    regime = a.selectbox("Regime atual", regimes, index=regimes.index(sugerido or c.regime_atual),
                         help="No Simples, ICMS/ISS do Presumido/Real são estimados pelas alíquotas abaixo.")
    anexos = ["III", "IV", "V", "fator_r"]
    anexo = b.selectbox("Anexo das notas de serviço", anexos, index=anexos.index(c.anexo_servico),
                        format_func={"III": "Anexo III", "IV": "Anexo IV", "V": "Anexo V",
                                     "fator_r": "Fator R (III ou V pela folha)"}.get)
    lr = d.selectbox("Lucro Real — apuração", ["trimestral", "anual"], index=["trimestral", "anual"].index(c.lr_periodo))

    st.subheader("Alíquotas do cliente")
    a, b, d = st.columns(3)
    iss = a.number_input("ISS do município (%)", 0.0, 5.0, c.iss_aliquota * 100, 0.01) / 100
    icms_s = b.number_input("ICMS médio nas saídas (%)", 0.0, 30.0, c.icms_aliquota_saida * 100, 0.5) / 100
    icms_e = d.number_input("ICMS médio nas compras (%)", 0.0, 30.0, c.icms_aliquota_entrada * 100, 0.5) / 100
    a, b, d, e = st.columns(4)
    rat = a.number_input("RAT (%)", 0.0, 3.0, c.rat * 100, 1.0) / 100
    fap = b.number_input("FAP", 0.5, 2.0, c.fap, 0.01)
    terceiros = d.number_input("Terceiros (%)", 0.0, 6.0, c.terceiros * 100, 0.1) / 100
    incluir_cpp = e.checkbox("Fator R inclui a CPP do DAS", c.fator_r_incluir_cpp, help="[CONFERIR] Res. CGSN 140, art. 26")

    st.subheader("Lucro Real — saldos e estimativa")
    a, b, d = st.columns(3)
    prej = a.number_input("Prejuízo fiscal a compensar (R$)", 0.0, value=float(c.prejuizo_fiscal_inicial), step=1000.0)
    bneg = b.number_input("Base negativa de CSLL (R$)", 0.0, value=float(c.base_negativa_inicial), step=1000.0)
    lucro = d.number_input("Lucro anual estimado (R$) — só se não houver DRE", 0.0,
                           value=float(c.lucro_anual_estimado or 0.0), step=10000.0)

    st.subheader("Reforma e projeção")
    a, b = st.columns(2)
    cbs = a.number_input("CBS — alíquota de referência (%)", 5.0, 15.0,
                         float(c.reforma.get("cbs_referencia", 0.0921)) * 100, 0.01,
                         help="[CONFERIR] O Senado fixa a alíquota de 2027 até 15/12/2026.") / 100
    ibs = b.number_input("IBS — alíquota de referência (%)", 10.0, 25.0,
                         float(c.reforma.get("ibs_referencia", 0.187)) * 100, 0.01) / 100
    a, b, d, e, f = st.columns(5)
    p = c.projecao
    meses = a.number_input("Meses projetados", 1, 12, p.meses)
    janela = b.number_input("Janela do histórico", 3, 24, p.janela)
    metodo = d.selectbox("Cenário Neutro", ["tendencia", "media"], ["tendencia", "media"].index(p.metodo),
                         format_func={"tendencia": "Tendência linear", "media": "Média"}.get)
    otim = e.number_input("Otimista (%)", 0.0, 100.0, p.otimista * 100, 1.0) / 100
    pess = f.number_input("Pessimista (%)", -100.0, 0.0, p.pessimista * 100, 1.0) / 100
    obs = st.text_area("Observações", c.observacoes)
    salvar = st.form_submit_button("Salvar cadastro", type="primary", icon=":material/save:")

if salvar:
    if not nome.strip():
        st.error("Informe a razão social.")
        st.stop()
    antigo_id = c.id if c.nome else None
    novo_c = Cliente(nome=nome.strip(), cnpj=cnpj.strip(), municipio=municipio, uf=uf.upper(), atividade=atividade,
                     regime_atual=regime, anexo_servico=anexo, iss_aliquota=iss, icms_aliquota_saida=icms_s,
                     icms_aliquota_entrada=icms_e, rat=rat, fap=fap, terceiros=terceiros,
                     fator_r_incluir_cpp=incluir_cpp, lr_periodo=lr, prejuizo_fiscal_inicial=prej,
                     base_negativa_inicial=bneg, lucro_anual_estimado=lucro or None,
                     presuncao=c.presuncao, reforma={"cbs_referencia": cbs, "ibs_referencia": ibs},
                     projecao=Projecao(meses=int(meses), janela=int(janela), metodo=metodo, otimista=otim, pessimista=pess,
                                       sazonalidade=p.sazonalidade),
                     depara=c.depara, observacoes=obs, socios=c.socios, distribuicao_lucro=c.distribuicao_lucro,
                     distribuicao_forma=c.distribuicao_forma, cnae=rf.cnae_principal if rf else c.cnae,
                     dados_receita=rf.como_dict() if rf else c.dados_receita)
    if importar_socios:
        novo_c.socios = [Socio(nome=s.nome.title(), participacao=1 / len(socios_qsa)) for s in socios_qsa]
    if antigo_id and antigo_id != novo_c.id:
        st.warning("Nome/CNPJ mudaram: o cadastro foi salvo numa pasta nova. Os dados antigos continuam na pasta anterior.")
    novo_c.salvar()
    st.session_state["cliente_id"] = novo_c.id
    st.session_state.pop("receita", None)
    st.session_state.pop("novo_cliente", None)
    st.session_state["cadastro_salvo"] = True
    st.rerun()
