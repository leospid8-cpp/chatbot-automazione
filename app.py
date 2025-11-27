import streamlit as st
import google.generativeai as genai
import pypdf
import json
import time
from backend import Database, MacchinaService, CommessaService

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agente Fabbrica 5.0", page_icon="🤖", layout="wide")

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
# FUNZIONE SPECIALE: L'ESECUTORE
# ==========================================
def esegui_azione_ai(azione_json):
    """Questa funzione è la 'mano' dell'AI che tocca il database"""
    try:
        # Tenta di convertire la stringa in dizionario
        dati = json.loads(azione_json)
        comando = dati.get("comando")
        
        if comando == "aggiorna_commessa":
            codice = dati.get("codice")
            nuovo_stato = dati.get("stato")
            # Convertiamo in minuscolo per confronto sicuro, ma salviamo come arriva
            st.session_state.commessa_service.update_commessa(codice, nuovo_stato)
            return f"✅ ESEGUITO: Ho aggiornato la commessa {codice} allo stato '{nuovo_stato}'."
            
        elif comando == "nuova_commessa":
            codice = dati.get("codice")
            prodotto = dati.get("prodotto")
            quantita = dati.get("quantita")
            st.session_state.commessa_service.add_commessa(codice, prodotto, quantita)
            return f"✅ ESEGUITO: Ho creato la commessa {codice} per {quantita}x {prodotto}."

        elif comando == "aggiorna_macchina":
            nome = dati.get("nome")
            stato = dati.get("stato")
            st.session_state.macchina_service.update_machine(nome, stato)
            return f"✅ ESEGUITO: Macchina {nome} impostata su {stato}."

        return "⚠️ Azione richiesta ma comando non riconosciuto."
    except json.JSONDecodeError:
        return "❌ Errore: L'AI ha generato un codice non valido."
    except Exception as e:
        return f"❌ Errore nell'esecuzione dell'azione: {e}"

# ==========================================
# BARRA LATERALE (Funzioni Manuali)
# ==========================================
with st.sidebar:
    st.title("🔧 Pannello Controllo")
    st.info("Ora puoi chiedere le modifiche direttamente in chat!")
    
    # --- MANUALI PDF ---
    st.subheader("📚 RAG (Manuali)")
    uploaded_file = st.file_uploader("Carica Manuale PDF", type="pdf")
    testo_manuale = ""
    if uploaded_file:
        try:
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                testo_manuale += page.extract_text() + "\n"
            st.success("Manuale caricato!")
        except:
            st.error("Errore PDF")

    st.divider()

    # --- COMANDI MANUALI ---
    with st.expander("➕ Aggiungi Macchina"):
        n = st.text_input("Nome Macchina")
        s = st.selectbox("Stato", ["Attiva", "Ferma", "Errore"])
        if st.button("Salva"):
            st.session_state.macchina_service.add_machine(n, s)
            st.rerun()

# ==========================================
# CHATBOT AGENTE
# ==========================================
st.title("🤖 Agente di Fabbrica (Legge e Scrive)")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ciao! Sono pronto. Posso leggere i dati e modificare il database se me lo chiedi."}]

# Mostra storico
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input utente
prompt = st.chat_input("Es: 'Imposta la commessa A1 come Completata'")

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 1. Recupero dati aggiornati
    dati_macchine = st.session_state.macchina_service.get_all_machines()
    dati_commesse = st.session_state.commessa_service.get_all_commesse()
    
    # 2. Prompt Tecnico
    full_prompt = f"""
    Sei l'Agente Operativo della fabbrica.
    
    DATI ATTUALI:
    {dati_macchine}
    ---
    {dati_commesse}
    
    DOMANDA UTENTE: {prompt}
    
    ISTRUZIONI:
    1. Se l'utente chiede informazioni, rispondi normalmente.
    2. Se l'utente vuole MODIFICARE o CREARE, rispondi SOLO con un JSON.
    
    FORMATI JSON (Rispetta questi campi esatti):
    - Aggiorna commessa: {{"comando": "aggiorna_commessa", "codice": "...", "stato": "..."}}
    - Nuova commessa: {{"comando": "nuova_commessa", "codice": "...", "prodotto": "...", "quantita": 100}}
    - Aggiorna macchina: {{"comando": "aggiorna_macchina", "nome": "...", "stato": "..."}}
    
    IMPORTANTE: Scrivi SOLO il JSON senza commenti, oppure rispondi a parole se non devi fare azioni.
    """
    
    # 3. Generazione e Controllo Azione
    with st.chat_message("assistant"):
        with st.spinner("Elaborazione..."):
            try:
                response = model.generate_content(full_prompt)
                risposta_ai = response.text.strip()
                
                # --- CERVELLO ESECUTIVO (Nuova logica robusta) ---
                json_da_eseguire = None
                
                # Caso A: JSON dentro blocchi markdown ```json ... ```
                if "```json" in risposta_ai:
                    try:
                        start = risposta_ai.find("```json") + 7
                        end = risposta_ai.find("```", start)
                        json_da_eseguire = risposta_ai[start:end].strip()
                    except:
                        pass
                
                # Caso B: JSON puro o sporco nel testo (cerca le graffe)
                elif "{" in risposta_ai and "}" in risposta_ai:
                    start = risposta_ai.find("{")
                    end = risposta_ai.rfind("}") + 1
                    json_da_eseguire = risposta_ai[start:end]

                # --- ESECUZIONE ---
                if json_da_eseguire:
                    # Proviamo a eseguirlo
                    esito = esegui_azione_ai(json_da_eseguire)
                    
                    if "❌" in esito:
                        # Se è fallito il parsing, stampiamo l'errore o il testo originale
                        st.write(risposta_ai)
                        st.warning(f"Tentativo azione fallito: {esito}")
                    else:
                        # Successo!
                        st.success(esito)
                        st.session_state.messages.append({"role": "assistant", "content": esito})
                        
                        # Ricarica pagina per mostrare i dati nuovi
                        time.sleep(2)
                        st.rerun()
                else:
                    # Risposta normale (parlata)
                    st.write(risposta_ai)
                    st.session_state.messages.append({"role": "assistant", "content": risposta_ai})

            except Exception as e:
                st.error(f"Errore critico: {e}")
