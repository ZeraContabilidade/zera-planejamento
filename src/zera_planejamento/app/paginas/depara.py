"""De-Para do cliente: regras próprias que valem antes das regras padrão."""
import pandas as pd
import streamlit as st

from zera_planejamento.app.estado import exigir_cliente
from zera_planejamento.dominio import DESTINOS, PADRAO, DePara
from zera_planejamento.dominio.depara import TIPOS

c = exigir_cliente()
st.title("De-Para Domínio → base mensal")
st.markdown(
    "Regras **deste cliente**, aplicadas antes das padrão. Exemplos: uniformes e EPI de empresa de manutenção "
    "(`CFOP_ENTRADA` `2556` → insumos, Lei 10.833/03, art. 3º, X); uma conta da DRE indedutível "
    "(`DRE_CONTA` `4.2.1.06.000008` → despesa indedutível); um fornecedor específico (`FORNECEDOR` `ROLAMENTOS`).")

destinos = list(DESTINOS)
df = pd.DataFrame(c.depara or [], columns=["tipo", "chave", "destino", "obs"])
editado = st.data_editor(
    df, num_rows="dynamic", width="stretch", hide_index=True,
    column_config={
        "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS, required=True),
        "chave": st.column_config.TextColumn("Chave", required=True, help="CFOP (1556 ou *556), código, trecho do nome..."),
        "destino": st.column_config.SelectboxColumn("Destino", options=destinos, required=True,
                                                    help="Coluna da base mensal ou tratamento especial"),
        "obs": st.column_config.TextColumn("Observação"),
    })
if st.button("Salvar regras do cliente", type="primary", icon=":material/save:"):
    c.depara = [{k: ("" if pd.isna(v) else str(v)) for k, v in r.items()} for r in editado.to_dict("records")
                if r.get("tipo") and r.get("chave") and r.get("destino")]
    invalidas = DePara.do_cliente(c).invalidas
    if invalidas:
        st.error(f"{len(invalidas)} regra(s) inválida(s).")
    else:
        c.salvar()
        st.success("Regras salvas. Importe os relatórios de novo para aplicar.")

with st.expander("Destinos possíveis"):
    st.dataframe(pd.DataFrame(DESTINOS.items(), columns=["Destino", "Significado"]), hide_index=True, width="stretch")
with st.expander(f"Regras padrão ({len(PADRAO)})"):
    st.dataframe(pd.DataFrame(DePara.para_dicts(PADRAO)), hide_index=True, width="stretch")
