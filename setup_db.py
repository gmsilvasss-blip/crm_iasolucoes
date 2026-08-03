import psycopg2
import secrets

DATABASE_URL_EXTERNA = "postgresql://crm_db_pzqd_user:d80acU2QMrrzv3FqUlKkRkZE5aBO5FQV@dpg-d9nbvgbm8hqs73e1b7tg-a.oregon-postgres.render.com/crm_db_pzqd"

def atualizar_banco():
    try:
        conn = psycopg2.connect(DATABASE_URL_EXTERNA)
        cur = conn.cursor()

        # 1. Renomear 'contato' para 'telefone' (se existir)
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='leads' AND column_name='contato';")
        if cur.fetchone():
            cur.execute("ALTER TABLE leads RENAME COLUMN contato TO telefone;")
        
        # 2. Adicionar novas colunas na tabela de leads
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS email VARCHAR(255);")
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS endereco TEXT;")
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Qualificação';")

        # 3. Adicionar token público para a captura de leads
        cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS token_publico VARCHAR(50) UNIQUE;")
        
        # Gerar tokens para usuários antigos que não têm
        cur.execute("SELECT id FROM usuarios WHERE token_publico IS NULL;")
        for u in cur.fetchall():
            token = secrets.token_hex(8) # Gera um código como 'a1b2c3d4'
            cur.execute("UPDATE usuarios SET token_publico = %s WHERE id = %s;", (token, u[0]))

        # 4. Criar a tabela de Produtos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                nome VARCHAR(100) NOT NULL,
                descricao TEXT
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Sucesso! Banco de dados atualizado com as novas estruturas.")
        
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == '__main__':
    atualizar_banco()