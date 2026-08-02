import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import json

app = Flask(__name__)

# Configurações de Segurança e Banco de Dados
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_desenvolvimento")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- FUNÇÃO AUXILIAR: CONEXÃO COM O BANCO ---
def conectar_banco():
    """Cria e retorna uma conexão com o banco de dados PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


# --- ROTA 1: TELA INICIAL PÚBLICA ---
@app.route('/')
def inicio():
    # Se o usuário já estiver logado e tentar acessar a raiz, joga direto pro Dashboard
    if 'usuario_id' in session:
        return redirect(url_for('home'))
    return render_template('inicio.html')


# --- ROTA 2: TELA DE LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        try:
            conn = conectar_banco()
            cur = conn.cursor()
            cur.execute("SELECT id, senha_hash FROM usuarios WHERE email = %s", (email,))
            usuario = cur.fetchone()
            cur.close()
            conn.close()

            if usuario and check_password_hash(usuario[1], senha):
                session['usuario_id'] = usuario[0]
                return redirect(url_for('home'))
            else:
                return "<h1>Erro: E-mail ou senha incorretos.</h1><br><a href='/login'>Tentar novamente</a>", 401

        except Exception as e:
            return f"<h1>Falha na conexão com o banco de dados.</h1><p>Erro: {e}</p>", 500

    return render_template('login.html')


# --- ROTA 3: TELA DE REGISTRO ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        senha = request.form.get('senha')
        
        senha_criptografada = generate_password_hash(senha)
        
        try:
            conn = conectar_banco()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO usuarios (email, telefone, senha_hash) VALUES (%s, %s, %s)",
                (email, telefone, senha_criptografada)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            return redirect(url_for('login'))
            
        except psycopg2.IntegrityError:
            return "<h1>Erro: Este e-mail já está cadastrado.</h1><br><a href='/registro'>Tentar novamente</a>", 400
        except Exception as e:
            return f"<h1>Erro interno ao tentar cadastrar.</h1><p>Erro: {e}</p>", 500

    return render_template('registro.html')


# --- ROTA 4: LOGOUT (SAIR DO SISTEMA) ---
@app.route('/logout')
def logout():
    # Remove o ID do usuário da sessão atual e joga pra tela inicial
    session.pop('usuario_id', None)
    return redirect(url_for('inicio'))


# --- ROTA 5: DASHBOARD (HOME) ---
@app.route('/home')
def home():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    proximo_compromisso = None
    eventos_calendario = []
    
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        
        # 1. Busca o próximo compromisso para exibir no card
        cur.execute("""
            SELECT titulo_compromisso, data_hora 
            FROM agenda 
            WHERE usuario_id = %s AND data_hora >= CURRENT_TIMESTAMP 
            ORDER BY data_hora ASC 
            LIMIT 1
        """, (session['usuario_id'],))
        resultado = cur.fetchone()
        
        if resultado:
            titulo = resultado[0]
            hora_formatada = resultado[1].strftime('%H:%M')
            proximo_compromisso = f"{hora_formatada} - {titulo}"
            
        # 2. Busca TODOS os compromissos do usuário para marcar no Calendário
        cur.execute("""
            SELECT titulo_compromisso, data_hora 
            FROM agenda 
            WHERE usuario_id = %s
        """, (session['usuario_id'],))
        todos_resultados = cur.fetchall()
        
        for t in todos_resultados:
            eventos_calendario.append({
                "titulo": t[0],
                "data": t[1].strftime('%Y-%m-%d'),
                "hora": t[1].strftime('%H:%M')
            })
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Aviso - Banco de dados: {e}")
        pass
    
    # Envia o próximo compromisso e a lista completa (em formato JSON) para o HTML
    return render_template('home.html', 
                           compromisso=proximo_compromisso, 
                           eventos_json=json.dumps(eventos_calendario))


# --- ROTA 6: SALVAR NA AGENDA ---
@app.route('/minha_agenda', methods=['POST'])
def minha_agenda():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    titulo = request.form.get('titulo_compromisso')
    data_hora = request.form.get('data_hora') # Espera o formato YYYY-MM-DD HH:MM
    
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        
        # Insere o compromisso atrelado ao ID do usuário logado
        cur.execute(
            "INSERT INTO agenda (usuario_id, titulo_compromisso, data_hora, status) VALUES (%s, %s, %s, 'Pendente')",
            (session['usuario_id'], titulo, data_hora)
        )
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Erro ao salvar na agenda: {e}")
        
    # Redireciona de volta para a Home para ver o card atualizado
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)