import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import datetime

class Database:
    def __init__(self):
        # Legge la password sicura dai Secrets di Streamlit
        try:
            self.db_url = st.secrets["SUPABASE_URL"]
        except:
            st.error("❌ Errore: Manca 'SUPABASE_URL' nei secrets.toml o su Cloud.")
            st.stop()

    def query(self, sql, params=()):
        conn = None
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(sql, params)
            
            if sql.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            else:
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Errore Database: {e}")
            return []
        finally:
            if conn:
                conn.close()

# --- GESTIONE MACCHINE ---
class MacchinaService:
    def __init__(self, db):
        self.db = db
        self.init_table()

    def init_table(self):
        self.db.query("""
            CREATE TABLE IF NOT EXISTS macchine (
                id SERIAL PRIMARY KEY,
                nome TEXT,
                stato TEXT
            );
        """)
        # Dati di prova
        if not self.db.query("SELECT * FROM macchine"):
            self.db.query("INSERT INTO macchine (nome, stato) VALUES (%s, %s)", ('Fresatrice A1', 'Attiva'))

    def get_all_machines(self):
        data = self.db.query("SELECT * FROM macchine ORDER BY id")
        if not data: return "Nessuna macchina registrata."
        return "\n".join([f"- {m['nome']} [Stato: {m['stato']}]" for m in data])

    def get_machine_names(self):
        data = self.db.query("SELECT nome FROM macchine ORDER BY id")
        return [m['nome'] for m in data]

    def add_machine(self, nome, stato):
        self.db.query("INSERT INTO macchine (nome, stato) VALUES (%s, %s)", (nome, stato))

    def update_machine(self, nome_macchina, nuovo_stato):
        self.db.query("UPDATE macchine SET stato = %s WHERE nome = %s", (nuovo_stato, nome_macchina))

# --- GESTIONE COMMESSE (FINANZIARIA) ---
class CommessaService:
    def __init__(self, db):
        self.db = db
        self.init_table()

    def init_table(self):
        # Crea la tabella con i campi economici e le date
        self.db.query("""
            CREATE TABLE IF NOT EXISTS commesse (
                id SERIAL PRIMARY KEY,
                codice TEXT,
                prodotto TEXT,
                quantita INTEGER,
                stato TEXT DEFAULT 'Pianificata',
                costo_materiale DECIMAL(10,2) DEFAULT 0,
                costo_lavorazione DECIMAL(10,2) DEFAULT 0,
                prezzo_vendita DECIMAL(10,2) DEFAULT 0,
                data_creazione DATE DEFAULT CURRENT_DATE,
                data_chiusura DATE
            );
        """)

    # 1. Crea Nuova (Con Prezzi)
    def add_commessa(self, codice, prodotto, quantita, c_mat, c_lav, p_vend):
        self.db.query(
            """INSERT INTO commesse 
               (codice, prodotto, quantita, costo_materiale, costo_lavorazione, prezzo_vendita) 
               VALUES (%s, %s, %s, %s, %s, %s)""", 
            (codice, prodotto, quantita, c_mat, c_lav, p_vend)
        )

    # 2. Leggi Tutte (Formatta i dati per l'AI)
    def get_all_commesse(self):
        data = self.db.query("SELECT * FROM commesse ORDER BY id DESC")
        if not data: return "Nessuna commessa registrata."
        
        report = []
        for c in data:
            # Prepariamo una stringa ricca di dati per l'AI
            spese = float(c['costo_materiale']) + float(c['costo_lavorazione'])
            utile = float(c['prezzo_vendita']) - spese
            
            dettaglio = (
                f"- Commessa {c['codice']} ({c['stato']}): {c['quantita']}x {c['prodotto']}. "
                f"[Finanza: Materiali={c['costo_materiale']}€, Lavorazione={c['costo_lavorazione']}€, "
                f"Vendita={c['prezzo_vendita']}€ -> UTILE STIMATO: {utile}€]. "
                f"Data Inserimento: {c['data_creazione']}."
            )
            
            if c['data_chiusura']:
                dettaglio += f" CHIUSA IL: {c['data_chiusura']}"
            
            report.append(dettaglio)
            
        return "\n".join(report)

    # 3. Lista Codici
    def get_commessa_codes(self):
        data = self.db.query("SELECT codice FROM commesse ORDER BY id DESC")
        return [c['codice'] for c in data]

    # 4. Aggiorna Stato (Gestisce la data di chiusura)
    def update_commessa(self, codice, nuovo_stato):
        if nuovo_stato == "Completata":
            self.db.query("UPDATE commesse SET stato = %s, data_chiusura = CURRENT_DATE WHERE codice = %s", (nuovo_stato, codice))
        else:
            self.db.query("UPDATE commesse SET stato = %s WHERE codice = %s", (nuovo_stato, codice))
