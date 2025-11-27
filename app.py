import streamlit as st
import google.generativeai as genai
import pypdf
from backend import Database, MacchinaService, CommessaService

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Fabbrica AI 4.0", page_icon="🏭", layout="wide")

# --- CONFIGURAZIONE AI ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.0-flash')
except:
    st.error("❌ Manca la chiave API Google nei secrets.")
    st.stop()

# --- INIZIALIZZAZIONE SERVIZI ---
if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.macchina_service = MacchinaService(st.session_state.db)
    st.session_state.commessa_service = CommessaService(st.session_state.db)

# ==========================================
# BARRA LATERALE (ADMIN & PDF)
# ==========================================
with st.sidebar:
    st.title("🔧 Pannello Controllo")
    
    # --- SEZIONE 1: MANUALI PDF ---
    st.subheader("📚 Documentazione (RAG)")
    uploaded_file = st.file_uploader("Carica Manuale PDF", type="pdf")
    testo_manuale = ""
    if uploaded_file:
        try:
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                testo_manuale += page.extract_text() + "\n"
            st.success(f"Manuale caricato! ({len(reader.pages)} pag.)")
        except:
            st.error("Errore lettura PDF")

    st.divider()
    
    # --- SEZIONE 2: AMMINISTRAZIONE ---
    st.subheader("🛠️ Gestione Fabbrica")
    
    # A. NUOVA MACCHINA
    with st.expander("➕ Nuova Macchina"):
        n_macchina = st.text_input("Nome")
        s_macchina = st.selectbox("Stato", ["Attiva", "Ferma", "Manutenzione", "Errore"])
        if st.button("Salva Macchina"):
            st.session_state.macchina_service.add_machine(n_macchina, s_macchina)
            st.success("Salvata!")
            st.rerun()

    # B. AGGIORNA STATO MACCHINA
    with st.expander("✏️ Aggiorna Macchina"):
        nomi = st.session_state.macchina_service.get_machine_names()
        if nomi:
            m_scelta = st.selectbox("Seleziona Macchina", nomi)
            nuova_nota = st.text_area("Nuovo Stato / Direttiva")
            if st.button("Aggiorna Macchina"):
                st.session_state.macchina_service.update_machine(m_scelta, nuova_nota)
                st.success("Aggiornato!")
                st.rerun()
        else:
            st.warning("Nessuna macchina.")

    # C. NUOVA COMMESSA
    with st.expander("📄 Crea Commessa"):
        cod_c = st.text_input("Codice (es. JOB-101)")
        prod_c = st.text_input("Prodotto")
        qta_c = st.number_input("Quantità", min_value=1, value=100)
        if st.button("Registra Commessa"):
            st.session_state.commessa_service.add_commessa(cod_c, prod_c, qta_c)
            st.success("Commessa Inserita!")
            st.rerun()

    # D. AGGIORNA STATO COMMESSA (NUOVO!)
    with st.expander("✅ Aggiorna Commessa"):
        codici = st.session_state.commessa_service.get_commessa_codes()
        if codici:
            c_sel = st.selectbox("Scegli Commessa", codici)
            s_new = st.selectbox("Nuovo Stato", ["Pianificata", "In Lavorazione", "Completata", "Sospesa"])
            
            if st.button("Cambia Stato Commessa"):
                st.session_state.commessa_service.update_commessa(c_sel, s_new)
                st.success(f"Stato aggiornato a: {s_new}")
                st.rerun()
        else:
            st.info("Nessuna commessa presente.")

# ==========================================
# CHATBOT PRINCIPALE
# ==========================================
st.title("🏭 Assistente di Produzione 4.0")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ciao! Sono connesso al Cloud. Gestisco macchine, commesse e leggo i manuali."}]

# Mostra storico
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input utente
prompt = st.chat_input("Chiedi stato impianto, dettagli commesse o soluzioni ai guasti...")

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 1. Recupero dati dal Cloud
    dati_macchine = st.session_state.macchina_service.get_all_machines()
    dati_commesse = st.session_state.commessa_service.get_all_commesse()
    
    # 2. Creazione Prompt Completo
    full_prompt = f"""
    Sei l'assistente AI della fabbrica.
    
    DATI IMPIANTO (Dal Database Cloud):
    {dati_macchine}
    
    COMMESSE ATTIVE:
    {dati_commesse}
    
    MANUALE TECNICO (Se caricato):
    {testo_manuale if testo_manuale else "Nessun manuale caricato."}
    
    DOMANDA UTENTE: {prompt}
    
    Rispondi in modo preciso. Se serve, cita il manuale.
    """
    
    # 3. Generazione Risposta
    with st.chat_message("assistant"):
        with st.spinner("Analisi dati in corso..."):
            try:
                response = model.generate_content(full_prompt)
                st.write(response.text)
                
                # Token counter
                usage = response.usage_metadata
                st.caption(f"📊 Token usati: {usage.total_token_count}")
                
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Errore AI: {e}")
