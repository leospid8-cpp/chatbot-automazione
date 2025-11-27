import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

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
            
            # Se è una lettura (SELECT) ritorna i dati
            if sql.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            # Se è una scrittura (INSERT/UPDATE) conferma le modifiche
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
        # Dati di prova se vuota
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

# --- GESTIONE COMMESSE (Aggiornata) ---
class CommessaService:
    def __init__(self, db):
        self.db = db
        self.init_table()

    def init_table(self):
        self.db.query("""
            CREATE TABLE IF NOT EXISTS commesse (
                id SERIAL PRIMARY KEY,
                codice TEXT,
                prodotto TEXT,
                quantita INTEGER,
                stato TEXT DEFAULT 'Pianificata'
            );
        """)

    # 1. Crea Nuova
    def add_commessa(self, codice, prodotto, quantita):
        self.db.query(
            "INSERT INTO commesse (codice, prodotto, quantita) VALUES (%s, %s, %s)", 
            (codice, prodotto, quantita)
        )

    # 2. Leggi Tutte (Per l'AI)
    def get_all_commesse(self):
        data = self.db.query("SELECT * FROM commesse ORDER BY id DESC")
        if not data: return "Nessuna commessa attiva."
        return "\n".join([f"- Commessa {c['codice']}: {c['prodotto']} ({c['quantita']} pz) - Stato: {c['stato']}" for c in data])

    # 3. Ottieni lista Codici (Per il menu a tendina)
    def get_commessa_codes(self):
        data = self.db.query("SELECT codice FROM commesse ORDER BY id DESC")
        return [c['codice'] for c in data]

    # 4. Aggiorna Stato (es. Completata)
    def update_commessa(self, codice, nuovo_stato):
        self.db.query("UPDATE commesse SET stato = %s WHERE codice = %s", (nuovo_stato, codice))
