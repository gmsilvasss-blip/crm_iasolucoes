import psycopg2

# Cole aqui a sua URL Externa do Render (a mesma usada no setup_db.py)
DATABASE_URL_EXTERNA = "postgresql://crm_db_pzqd_user:d80acU2QMrrzv3FqUlKkRkZE5aBO5FQV@dpg-d9nbvgbm8hqs73e1b7tg-a.oregon-postgres.render.com/crm_db_pzqd"

def criar_tabela_agenda():
    try:
        print("Conectando ao banco de dados no Render...")
        conn = psycopg2.connect(DATABASE_URL_EXTERNA)
        cur = conn.cursor()
        
        # Cria a tabela vinculando o usuario_id à tabela usuarios
        query = """
        CREATE TABLE IF NOT EXISTS agenda (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            titulo_compromisso VARCHAR(255) NOT NULL,
            data_hora TIMESTAMP NOT NULL,
            status VARCHAR(50) DEFAULT 'Pendente'
        );
        """
        
        cur.execute(query)
        conn.commit()
        
        cur.close()
        conn.close()
        print("Sucesso! Tabela 'agenda' estruturada e pronta para receber dados.")
        
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == '__main__':
    criar_tabela_agenda()