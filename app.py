import streamlit as st
import google.generativeai as genai
import pypdf
import json
from backend import Database, MacchinaService, CommessaService

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agente Fabbrica 5.0", page_icon="🤖", layout="wide")

# --- CONFIGURAZIONE AI ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # Usiamo un modello che supporta bene il JSON
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
        dati = json.loads(azione_json)
        comando = dati.get("comando")
        
        if comando == "aggiorna_commessa":
            codice = dati.get("codice")
            nuovo_stato = dati.get("stato")
            # Chiama la funzione vera del database
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

        return "⚠️ Azione non riconosciuta."
    except Exception as e:
        return f"❌ Errore nell'esecuzione dell'azione: {e}"

# ==========================================
# BARRA LATERALE (Rimane uguale per le funzioni manuali)
# ==========================================
with st.sidebar:
    st.title("🔧 Pannello Controllo")
    st.info("Ora puoi anche chiedere in chat di modificare le cose!")
    
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

# ==========================================
# CHATBOT AGENTE
# ==========================================
st.title("🤖 Agente di Fabbrica (Legge e Scrive)")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ciao! Sono un Agente AI. Posso leggere il database e, se me lo chiedi, posso anche modificare commesse e stati macchina."}]

# Mostra storico
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input utente
prompt = st.chat_input("Es: 'Imposta la commessa JOB-101 come Completata' o 'La Fresatrice è in Errore'")

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 1. Recupero dati
    dati_macchine = st.session_state.macchina_service.get_all_machines()
    dati_commesse = st.session_state.commessa_service.get_all_commesse()
    
    # 2. Prompt Tecnico (Qui spieghiamo all'AI come "premere i bottoni")
    full_prompt = f"""
    Sei l'Agente Operativo della fabbrica.
    
    DATI ATTUALI:
    {dati_macchine}
    ---
    {dati_commesse}
    
    DOMANDA UTENTE: {prompt}
    
    ISTRUZIONI PER L'INTELLIGENZA ARTIFICIALE:
    1. Se l'utente chiede solo informazioni, rispondi normalmente.
    2. Se l'utente chiede di MODIFICARE o CREARE qualcosa, NON rispondere a parole.
       Invece, restituisci SOLO un oggetto JSON con il comando da eseguire.
    
    FORMATI JSON ACCETTATI PER LE AZIONI:
    - Per aggiornare commessa: {{"comando": "aggiorna_commessa", "codice": "...", "stato": "..."}}
    - Per nuova commessa: {{"comando": "nuova_commessa", "codice": "...", "prodotto": "...", "quantita": 100}}
    - Per aggiornare macchina: {{"comando": "aggiorna_macchina", "nome": "...", "stato": "..."}}
    
    IMPORTANTE: Se generi JSON, non scrivere altro testo prima o dopo.
    """
    
    # 3. Generazione e Controllo Azione
    with st.chat_message("assistant"):
        with st.spinner("Elaborazione..."):
            try:
                response = model.generate_content(full_prompt)
                risposta_ai = response.text.strip()
                
                # VERIFICA: L'AI vuole fare un'azione? (Cerca parentesi graffe)
                if risposta_ai.startswith("{") and risposta_ai.endswith("}"):
                    # È UN COMANDO JSON! Eseguiamolo.
                    esito = esegui_azione_ai(risposta_ai)
                    st.success(esito) # Mostra box verde
                    st.session_state.messages.append({"role": "assistant", "content": esito})
                    
                    # Ricarichiamo la pagina dopo un attimo per aggiornare i dati a video
                    import time
                    time.sleep(2)
                    st.rerun()
                else:
                    # È UNA RISPOSTA NORMALE
                    st.write(risposta_ai)
                    st.session_state.messages.append({"role": "assistant", "content": risposta_ai})

            except Exception as e:
                st.error(f"Errore AI: {e}")
