import psycopg2

# URL Externa para rodar o script a partir do seu computador local
DATABASE_URL_EXTERNA = "postgresql://crm_db_pzqd_user:d80acU2QMrrzv3FqUlKkRkZE5aBO5FQV@dpg-d9nbvgbm8hqs73e1b7tg-a.oregon-postgres.render.com/crm_db_pzqd"

def criar_tabela():
    try:
        print("Conectando ao banco de dados no Render...")
        conn = psycopg2.connect(DATABASE_URL_EXTERNA)
        cur = conn.cursor()
        
        # Comando SQL para criar a tabela de usuários
        query = """
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            telefone VARCHAR(50),
            senha_hash VARCHAR(255) NOT NULL
        );
        """
        
        cur.execute(query)
        conn.commit()
        
        cur.close()
        conn.close()
        print("Sucesso! Tabela 'usuarios' criada e pronta para uso.")
        
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == '__main__':
    criar_tabela()