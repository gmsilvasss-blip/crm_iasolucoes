import psycopg2

DATABASE_URL_EXTERNA = "postgresql://crm_db_pzqd_user:d80acU2QMrrzv3FqUlKkRkZE5aBO5FQV@dpg-d9nbvgbm8hqs73e1b7tg-a.oregon-postgres.render.com/crm_db_pzqd"

def reparo_banco():
    try:
        conn = psycopg2.connect(DATABASE_URL_EXTERNA)
        cur = conn.cursor()
        
        print("Verificando estrutura do banco de dados...")

        # 1. Repara a tabela agenda (garante que status e observacoes existem)
        cur.execute("ALTER TABLE agenda ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Pendente';")
        cur.execute("ALTER TABLE agenda ADD COLUMN IF NOT EXISTS observacoes TEXT;")
        cur.execute("UPDATE agenda SET status = 'Pendente' WHERE status IS NULL;")
        
        # 2. Garante que a tabela de Leads existe (caso o setup anterior não tenha rodado)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            nome VARCHAR(255) NOT NULL,
            empresa VARCHAR(255),
            interesse VARCHAR(255),
            contato VARCHAR(50)
        );
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("Sucesso! Reparo concluído. Todas as colunas e tabelas estão prontas.")
        
    except Exception as e:
        print(f"Ocorreu um erro ao reparar o banco: {e}")

if __name__ == '__main__':
    reparo_banco()