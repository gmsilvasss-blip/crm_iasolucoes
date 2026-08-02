import psycopg2

DATABASE_URL_EXTERNA = "postgresql://crm_db_pzqd_user:d80acU2QMrrzv3FqUlKkRkZE5aBO5FQV@dpg-d9nbvgbm8hqs73e1b7tg-a.oregon-postgres.render.com/crm_db_pzqd"

def vincular_tabelas():
    try:
        conn = psycopg2.connect(DATABASE_URL_EXTERNA)
        cur = conn.cursor()
        
        # Adiciona a coluna lead_id na agenda, vinculando ao cliente. 
        # ON DELETE CASCADE = se o lead for apagado, a agenda dele também será.
        cur.execute("ALTER TABLE agenda ADD COLUMN IF NOT EXISTS lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE;")
        
        conn.commit()
        cur.close()
        conn.close()
        print("Sucesso! Tabela de agenda agora está conectada à Base de Leads.")
        
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == '__main__':
    vincular_tabelas()