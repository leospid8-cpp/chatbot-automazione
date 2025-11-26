import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

class Database:
    def __init__(self):
        # ORA LEGGE LA PASSWORD DALLA CASSAFORTE (SECRETS)
        # Se sei in locale e ti dà errore, crea la cartella .streamlit/secrets.toml
        try:
            self.db_url = st.secrets["SUPABASE_URL"]
        except:
            st.error("Manca il secret SUPABASE_URL!")

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
            st.error(f"Errore DB: {e}")
            return []
        finally:
            if conn:
                conn.close()

# --- SERVIZIO MACCHINE ---
class MacchinaService:
    def __init__(self, db):
        self.db = db
        # init_table rimosso per sicurezza in cloud (si presume db già inizializzato)
        # ma se serve si può lasciare. Per ora teniamo il codice pulito.

    def get_all_machines(self):
        data = self.db.query("SELECT * FROM macchine ORDER BY id")
        if not data: return "Nessuna macchina."
        return "\n".join([f"- {m['nome']} [{m['stato']}]" for m in data])

    def get_machine_names(self):
        data = self.db.query("SELECT nome FROM macchine ORDER BY id")
        return [m['nome'] for m in data]

    def add_machine(self, nome, stato):
        self.db.query("INSERT INTO macchine (nome, stato) VALUES (%s, %s)", (nome, stato))

    def update_machine(self, nome_macchina, nuovo_stato):
        self.db.query("UPDATE macchine SET stato = %s WHERE nome = %s", (nuovo_stato, nome_macchina))

class CommessaService:
    def __init__(self, db):
        self.db = db