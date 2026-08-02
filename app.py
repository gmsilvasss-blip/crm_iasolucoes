import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2

app = Flask(__name__)

# Chave de segurança para os cookies de sessão (obrigatório para manter o usuário logado)
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_desenvolvimento")

# URL do banco de dados puxada das variáveis de ambiente do Render
DATABASE_URL = os.getenv("DATABASE_URL")


# --- ROTA 1: TELA INICIAL ---
@app.route('/')
def inicio():
    # Esta tela será o ponto de partida e também o destino após um login de sucesso
    return render_template('inicio.html')


# --- ROTA 2: TELA DE LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Captura os dados do formulário HTML
        email = request.form.get('email')
        senha = request.form.get('senha')

        try:
            # Conecta ao banco de dados
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            
            # Busca o id e o hash da senha do usuário correspondente ao email
            cur.execute("SELECT id, senha_hash FROM usuarios WHERE email = %s", (email,))
            usuario = cur.fetchone()
            
            cur.close()
            conn.close()

            # Validação: Se o usuário existir e a senha inserida bater com o hash salvo
            if usuario and check_password_hash(usuario[1], senha):
                # Salva o ID do usuário na sessão ativa
                session['usuario_id'] = usuario[0]
                
                # Encaminha para a tela inicial (rota '/')
                return redirect(url_for('inicio'))
            else:
                # Alerta de erro de usuário (credenciais inválidas)
                return "<h1>Erro: E-mail ou senha incorretos.</h1><br><a href='/login'>Tentar novamente</a>", 401

        except Exception as e:
            return f"<h1>Falha na conexão com o banco de dados.</h1><p>Erro: {e}</p>", 500

    # Se a requisição for GET (o usuário apenas clicou no link), exibe o formulário
    return render_template('login.html')


# --- ROTA 3: TELA DE REGISTRO ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Captura os dados preenchidos no formulário
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        senha = request.form.get('senha')
        
        # Criptografa a senha para segurança (nunca salvar em texto puro)
        senha_criptografada = generate_password_hash(senha)
        
        try:
            # Conecta ao banco
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            
            # Insere o novo usuário na tabela
            cur.execute(
                "INSERT INTO usuarios (email, telefone, senha_hash) VALUES (%s, %s, %s)",
                (email, telefone, senha_criptografada)
            )
            
            conn.commit()
            cur.close()
            conn.close()
            
            # Após o cadastro com sucesso, redireciona diretamente para a tela de login
            return redirect(url_for('login'))
            
        except psycopg2.IntegrityError:
            # Captura o erro caso o e-mail já exista no banco (devido à restrição UNIQUE)
            return "<h1>Erro: Este e-mail já está cadastrado no sistema.</h1><br><a href='/registro'>Tentar novamente</a>", 400
        except Exception as e:
            return f"<h1>Erro interno ao tentar cadastrar o usuário.</h1><p>Erro: {e}</p>", 500

    # Se for GET, mostra o formulário de cadastro
    return render_template('registro.html')


if __name__ == '__main__':
    app.run(debug=True)