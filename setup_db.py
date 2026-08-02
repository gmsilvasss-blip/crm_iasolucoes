import psycopg2

# Sua URL do Render
DATABASE_URL_EXTERNA = "postgresql://crm_db_pzqd_user:d80acU2QMrrzv3FqUlKkRkZE5aBO5FQV@dpg-d9nbvgbm8hqs73e1b7tg-a.oregon-postgres.render.com/crm_db_pzqd"

def criar_tabelas_leads():
    try:
        print("Conectando ao banco de dados no Render...")
        conn = psycopg2.connect(DATABASE_URL_EXTERNA)
        cur = conn.cursor()
        
        # 1. Tabela Principal de Leads
        query_leads = """
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            nome VARCHAR(255) NOT NULL,
            empresa VARCHAR(255),
            interesse VARCHAR(255),
            contato VARCHAR(50)
        );
        """
        cur.execute(query_leads)
        
        # 2. Tabela de Notas Contínuas (Histórico)
        query_notas = """
        CREATE TABLE IF NOT EXISTS notas_leads (
            id SERIAL PRIMARY KEY,
            lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
            nota VARCHAR(300) NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(query_notas)
        
        conn.commit()
        cur.close()
        conn.close()
        print("Sucesso! Tabelas 'leads' e 'notas_leads' criadas.")
        
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == '__main__':
    criar_tabelas_leads()