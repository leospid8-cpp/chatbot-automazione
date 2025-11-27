import streamlit as st
import google.generativeai as genai
import pypdf
import json
import time
from backend import Database, MacchinaService, CommessaService

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestionale Fabbrica AI", page_icon="💰", layout="wide")

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.0-flash')
except:
    st.error("❌ Manca la chiave API Google nei secrets.")
    st.stop()

# --- DATI ---
if "db" not in st.session_state:
    st.session_state.db = Database()
    st.session_state.macchina_service = MacchinaService(st.session_state.db)
    st.session_state.commessa_service = CommessaService(st.session_state.db)

# --- FUNZIONE AGENTE (Per modifiche via chat) ---
def esegui_azione_ai(azione_json):
    try:
        dati = json.loads(azione_json)
        comando = dati.get("comando")
        
        if comando == "aggiorna_commessa":
            st.session_state.commessa_service.update_commessa(dati.get("codice"), dati.get("stato"))
            return f"✅ Commessa {dati.get('codice')} aggiornata a {dati.get('stato')}."
        elif comando == "aggiorna_macchina":
            st.session_state.macchina_service.update_machine(dati.get("nome"), dati.get("stato"))
            return f"✅ Macchina {dati.get('nome')} aggiornata."
        # Nota: La creazione commessa via chat la teniamo semplice (senza prezzi) per ora
        elif comando == "nuova_commessa": 
            st.session_state.commessa_service.add_commessa(dati.get("codice"), dati.get("prodotto"), dati.get("quantita"), 0, 0, 0)
            return f"✅ Commessa base {dati.get('codice')} creata (aggiorna i prezzi dal pannello)."
        
        return "⚠️ Azione sconosciuta."
    except Exception as e:
        return f"❌ Errore: {e}"

# ==========================================
# BARRA LATERALE (ADMIN)
# ==========================================
with st.sidebar:
    st.title("🔧 Pannello Gestionale")
    
    # --- PDF ---
    st.subheader("📚 RAG")
    uploaded_file = st.file_uploader("Carica Manuale PDF", type="pdf")
    testo_manuale = ""
    if uploaded_file:
        try:
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages: testo_manuale += page.extract_text() + "\n"
            st.success("PDF Caricato!")
        except: st.error("Errore PDF")

    st.divider()

    # --- NUOVA COMMESSA CON PREZZI ---
    with st.expander("💰 Crea Commessa (Finanziaria)"):
        cod = st.text_input("Codice")
        prod = st.text_input("Prodotto")
        qta = st.number_input("Quantità", 1, 10000, 100)
        
        st.write("--- Dati Economici ---")
        c_mat = st.number_input("Costo Materiali Totale (€)", 0.0, step=10.0)
        c_lav = st.number_input("Costo Lavorazione Totale (€)", 0.0, step=10.0)
        p_ven = st.number_input("Prezzo Vendita Totale (€)", 0.0, step=50.0)
        
        if st.button("Registra Commessa"):
            st.session_state.commessa_service.add_commessa(cod, prod, qta, c_mat, c_lav, p_ven)
            st.success("Salvata nel Cloud!")
            st.rerun()

    # --- ALTRI COMANDI ---
    with st.expander("✏️ Aggiorna Macchina"):
        nomi = st.session_state.macchina_service.get_machine_names()
        if nomi:
            m = st.selectbox("Macchina", nomi)
            s = st.text_area("Nuovo Stato")
            if st.button("Aggiorna Stato Macchina"):
                st.session_state.macchina_service.update_machine(m, s)
                st.rerun()
                
    with st.expander("✅ Aggiorna Commessa"):
        codici = st.session_state.commessa_service.get_commessa_codes()
        if codici:
            c = st.selectbox("Codice", codici)
            s = st.selectbox("Nuovo Stato", ["Pianificata", "In Lavorazione", "Completata"])
            if st.button("Aggiorna Stato Commessa"):
                st.session_state.commessa_service.update_commessa(c, s)
                st.rerun()

# ==========================================
# CHATBOT ANALISTA
# ==========================================
st.title("📊 Assistente Fabbrica & Finanza")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ciao! Posso analizzare la produzione e i guadagni. Chiedimi un report mensile o l'analisi dei costi."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

prompt = st.chat_input("Es: 'Quanto abbiamo guadagnato questo mese?' o 'Analizza i costi della commessa A1'")

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Dati
    dati_macchine = st.session_state.macchina_service.get_all_machines()
    dati_commesse = st.session_state.commessa_service.get_all_commesse()
    
    full_prompt = f"""
    Sei un Analista di Produzione e Finanziario.
    
    DATI ECONOMICI E PRODUTTIVI (Dal Database):
    {dati_commesse}
    
    STATO MACCHINE:
    {dati_macchine}
    
    MANUALE: {testo_manuale[:1000] if testo_manuale else "Nessuno"}
    
    DOMANDA UTENTE: {prompt}
    
    ISTRUZIONI:
    1. Se l'utente chiede un REPORT o CALCOLI, usa i dati economici forniti (Spese, Ricavi, Utile) per fare somme e analisi precise.
    2. Se l'utente vuole MODIFICARE (es. "Metti la commessa X in Completata"), rispondi SOLO col JSON:
       {{"comando": "aggiorna_commessa", "codice": "...", "stato": "..."}} o 
       {{"comando": "aggiorna_macchina", "nome": "...", "stato": "..."}}
    """
    
    with st.chat_message("assistant"):
        with st.spinner("Analisi in corso..."):
            try:
                response = model.generate_content(full_prompt)
                risposta = response.text.strip()
                
                # Riconoscimento JSON (Agente)
                json_exec = None
                if "```json" in risposta:
                    s = risposta.find("```json") + 7
                    e = risposta.find("```", s)
                    json_exec = risposta[s:e].strip()
                elif risposta.startswith("{") and risposta.endswith("}"):
                    json_exec = risposta
                
                if json_exec:
                    esito = esegui_azione_ai(json_exec)
                    st.success(esito)
                    st.session_state.messages.append({"role": "assistant", "content": esito})
                    time.sleep(2)
                    st.rerun()
                else:
                    st.write(risposta)
                    st.session_state.messages.append({"role": "assistant", "content": risposta})
                    
            except Exception as e:
                st.error(f"Errore: {e}")
