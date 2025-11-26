import streamlit as st
import google.generativeai as genai
import pypdf
from backend import Database, MacchinaService, CommessaService

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Fabbrica AI", page_icon="🏭", layout="wide")

try:
    # LEGGE LA CHIAVE DALLA CASSAFORTE
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('models/gemini-2.0-flash')
except:
    st.error("Mancano le chiavi segrete! Configurale su Streamlit Cloud.")
    st.stop()

# --- CONNESSIONE DATI ---
if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.macchina_service = MacchinaService(st.session_state.db)

# --- SIDEBAR ---
with st.sidebar:
    st.header("📚 Documenti")
    uploaded_file = st.file_uploader("Carica Manuale PDF", type="pdf")
    testo_manuale = ""
    if uploaded_file:
        try:
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages: testo_manuale += page.extract_text()
            st.success("Manuale caricato!")
        except: st.error("Errore PDF")

    st.divider()
    st.header("🛠️ Admin")
    with st.expander("➕ Aggiungi Macchina"):
        n = st.text_input("Nome")
        s = st.selectbox("Stato", ["Attiva", "Ferma", "Errore"])
        if st.button("Salva"):
            st.session_state.macchina_service.add_machine(n, s)
            st.rerun()

    with st.expander("✏️ Aggiorna"):
        nomi = st.session_state.macchina_service.get_machine_names()
        if nomi:
            m = st.selectbox("Macchina", nomi)
            d = st.text_area("Stato/Note")
            if st.button("Aggiorna"):
                st.session_state.macchina_service.update_machine(m, d)
                st.rerun()

# --- CHAT ---
st.title("🏭 Assistente Fabbrica (Cloud)")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ciao! Sono online dal Cloud."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

prompt = st.chat_input("Scrivi qui...")
if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Contesto
    dati = st.session_state.macchina_service.get_all_machines()
    full_prompt = f"Dati Impianto:\n{dati}\n\nManuale:\n{testo_manuale}\n\nDomanda: {prompt}"
    
    with st.chat_message("assistant"):
        resp = model.generate_content(full_prompt)
        st.write(resp.text)
        st.session_state.messages.append({"role": "assistant", "content": resp.text})