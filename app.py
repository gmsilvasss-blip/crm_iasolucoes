import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2

app = Flask(__name__)

# Chave de segurança para os cookies de sessão (obrigatório)[cite: 1]
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_desenvolvimento")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- ROTA INICIAL (Resolve o Erro 404) ---
@app.route('/')
def inicio():
    return render_template('inicio.html')

# --- ROTA DE LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Substituímos request.json por request.form para ler o HTML
        identificador = request.form.get('email')
        senha = request.form.get('senha')

        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            
            # Busca o usuário pelo email inserido[cite: 1]
            cur.execute("SELECT id, senha_hash FROM usuarios WHERE email = %s", (identificador,))
            usuario = cur.fetchone()
            
            cur.close()
            conn.close()

            # Compara a senha digitada com o hash salvo no banco[cite: 1]
            if usuario and check_password_hash(usuario[1], senha):
                # Salva o ID do usuário na sessão ativa[cite: 1]
                session['usuario_id'] = usuario[0]
                return redirect(url_for('inicio')) # Retorna para o início após logar
            else:
                return "Email ou senha incorretos", 401

        except Exception as e:
            return "Falha na conexão com o banco de dados", 500

    # Se for GET (acessar a URL pelo navegador), mostra a tela HTML
    return render_template('login.html')

# --- ROTA DE REGISTRO ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Aqui entrará a lógica de inserção no banco
        pass
    return render_template('registro.html')

if __name__ == '__main__':
    app.run(debug=True)