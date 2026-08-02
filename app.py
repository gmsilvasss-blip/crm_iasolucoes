from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)

# Chave de segurança para os cookies de sessão (obrigatório)
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_desenvolvimento")
DATABASE_URL = os.getenv("DATABASE_URL")

@app.route('/login', methods=['POST'])
def login():
    dados = request.json
    identificador = dados.get('login')
    senha = dados.get('senha')

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Busca o usuário pelo email inserido
        cur.execute("SELECT id, senha_hash FROM usuarios WHERE email = %s", (identificador,))
        usuario = cur.fetchone()
        
        cur.close()
        conn.close()

        # Compara a senha digitada com o hash salvo no banco
        if usuario and check_password_hash(usuario[1], senha):
            # Salva o ID do usuário na sessão ativa
            session['usuario_id'] = usuario[0]
            return jsonify({"mensagem": "Acesso permitido", "redirecionar": "/crm"}), 200
        else:
            return jsonify({"erro": "Email ou senha incorretos"}), 401

    except Exception as e:
        return jsonify({"erro": "Falha na conexão"}), 500