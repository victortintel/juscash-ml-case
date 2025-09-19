import os, json, requests, streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Verificador (LLM)", page_icon="⚖️")
st.title("⚖️ Verificador de Processos (LLM)")

payload_default = {
    "numeroProcesso": "0001234-56.2023.4.05.8100",
    "siglaTribunal": "TRF5",
    "esfera": "Federal",
    "valorCondenacao": 67592,
    "documentos": [
        {"id": "DOC-1-2", "nome": "Certidão de Trânsito em Julgado", "texto": "Certifico o trânsito em julgado."},
        {"id": "DOC-1-4", "nome": "Requisição (RPV)", "texto": "Expede-se RPV em favor do exequente."}
    ],
    "movimentos": [
        {"descricao": "Iniciado cumprimento definitivo de sentença."}
    ]
}

st.caption("Cole aqui o JSON do processo (contrato mínimo do case).")
code = st.text_area("JSON do processo", value=json.dumps(payload_default, ensure_ascii=False, indent=2), height=320)

if st.button("Analisar"):
    try:
        data = json.loads(code)
        r = requests.post(f"{API_BASE}/predict", json=data, timeout=120)
        r.raise_for_status()
        st.subheader("Resposta")
        st.code(json.dumps(r.json(), ensure_ascii=False, indent=2), language="json")
    except Exception as e:
        st.error(str(e))

st.sidebar.markdown(f"**API**: `{API_BASE}`")
