import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2

app = Flask(__name__)

# Configurações de Segurança e Banco de Dados
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_desenvolvimento")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- FUNÇÃO AUXILIAR: CONEXÃO COM O BANCO ---
def conectar_banco():
    return psycopg2.connect(DATABASE_URL)


# ==========================================
# MÓDULO: AUTENTICAÇÃO
# ==========================================

@app.route('/')
def inicio():
    if 'usuario_id' in session:
        return redirect(url_for('home'))
    return render_template('inicio.html')

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

@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    return redirect(url_for('inicio'))


# ==========================================
# MÓDULO: AGENDA E DASHBOARD
# ==========================================

@app.route('/home')
def home():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    proximo_compromisso = None
    eventos_calendario = []
    lista_leads = [] 
    
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        
        # 1. Próximo compromisso Pendente
        cur.execute("""
            SELECT titulo_compromisso, data_hora 
            FROM agenda 
            WHERE usuario_id = %s AND data_hora >= CURRENT_TIMESTAMP AND status = 'Pendente'
            ORDER BY data_hora ASC LIMIT 1
        """, (session['usuario_id'],))
        resultado = cur.fetchone()
        
        if resultado:
            hora_formatada = resultado[1].strftime('%H:%M')
            proximo_compromisso = f"{hora_formatada} - {resultado[0]}"
            
        # 2. Busca TODOS os compromissos para o calendário
        cur.execute("""
            SELECT id, titulo_compromisso, data_hora, status, observacoes 
            FROM agenda WHERE usuario_id = %s
        """, (session['usuario_id'],))
        
        for t in cur.fetchall():
            eventos_calendario.append({
                "id": t[0],
                "titulo": t[1],
                "data": t[2].strftime('%Y-%m-%d'),
                "hora": t[2].strftime('%H:%M'),
                "status": t[3],
                "obs": t[4] if t[4] else ""
            })
            
        # 3. Busca todos os leads para o dropdown de agendamento
        cur.execute("SELECT nome, empresa FROM leads WHERE usuario_id = %s ORDER BY nome ASC", (session['usuario_id'],))
        for l in cur.fetchall():
            lista_leads.append({"nome": l[0], "empresa": l[1]})
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro BD Home: {e}")
    
    return render_template('home.html', compromisso=proximo_compromisso, eventos_json=json.dumps(eventos_calendario), leads=lista_leads)

@app.route('/minha_agenda', methods=['POST'])
def minha_agenda():
    if 'usuario_id' not in session: return redirect(url_for('login'))
        
    titulo = request.form.get('titulo_compromisso')
    data_str = request.form.get('data_compromisso') 
    hora_str = request.form.get('hora_compromisso') 
    data_hora_completa = f"{data_str} {hora_str}:00"
    
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO agenda (usuario_id, titulo_compromisso, data_hora, status) VALUES (%s, %s, %s, 'Pendente')",
            (session['usuario_id'], titulo, data_hora_completa)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro Agenda: {e}")
        
    return redirect(url_for('home'))

@app.route('/salvar_feedback', methods=['POST'])
def salvar_feedback():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    
    evento_id = request.form.get('evento_id')
    observacoes = request.form.get('observacoes')
    acao = request.form.get('acao') 
    
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        
        if acao == 'excluir':
            cur.execute("DELETE FROM agenda WHERE id = %s AND usuario_id = %s", (evento_id, session['usuario_id']))
        elif acao == 'reagendar':
            nova_data = request.form.get('data_compromisso')
            nova_hora = request.form.get('hora_compromisso')
            data_hora_completa = f"{nova_data} {nova_hora}:00"
            cur.execute(
                "UPDATE agenda SET observacoes = %s, status = 'Pendente', data_hora = %s WHERE id = %s AND usuario_id = %s",
                (observacoes, data_hora_completa, evento_id, session['usuario_id'])
            )
        else:
            cur.execute(
                "UPDATE agenda SET observacoes = %s, status = 'Concluído' WHERE id = %s AND usuario_id = %s",
                (observacoes, evento_id, session['usuario_id'])
            )
            
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro Feedback: {e}")
        
    return redirect(url_for('home'))


# ==========================================
# MÓDULO: BASE DE LEADS
# ==========================================

@app.route('/base_leads')
def base_leads():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    
    leads_processados = []
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        
        cur.execute("SELECT id, nome, empresa, interesse, contato FROM leads WHERE usuario_id = %s ORDER BY id DESC", (session['usuario_id'],))
        leads_db = cur.fetchall()
        
        for l in leads_db:
            lead_id = l[0]
            cur.execute("SELECT nota, data_criacao FROM notas_leads WHERE lead_id = %s ORDER BY data_criacao DESC", (lead_id,))
            notas_db = cur.fetchall()
            
            lista_notas = [{"texto": n[0], "data": n[1].strftime('%d/%m/%Y %H:%M')} for n in notas_db]
            
            leads_processados.append({
                "id": lead_id,
                "nome": l[1],
                "empresa": l[2],
                "interesse": l[3],
                "contato": l[4],
                "notas": lista_notas
            })
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao carregar leads: {e}")
        
    return render_template('base_leads.html', leads=leads_processados)

@app.route('/cadastrar_lead', methods=['POST'])
def cadastrar_lead():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    
    nome = request.form.get('nome')
    empresa = request.form.get('empresa')
    interesse = request.form.get('interesse')
    contato = request.form.get('contato')
    nota_inicial = request.form.get('nota')
    
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO leads (usuario_id, nome, empresa, interesse, contato) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (session['usuario_id'], nome, empresa, interesse, contato)
        )
        novo_lead_id = cur.fetchone()[0]
        
        if nota_inicial:
            cur.execute("INSERT INTO notas_leads (lead_id, nota) VALUES (%s, %s)", (novo_lead_id, nota_inicial[:300]))
            
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao cadastrar lead: {e}")
        
    return redirect(url_for('base_leads'))

@app.route('/editar_lead', methods=['POST'])
def editar_lead():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    
    lead_id = request.form.get('lead_id')
    nome = request.form.get('nome')
    empresa = request.form.get('empresa')
    interesse = request.form.get('interesse')
    contato = request.form.get('contato')
    
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute(
            "UPDATE leads SET nome=%s, empresa=%s, interesse=%s, contato=%s WHERE id=%s AND usuario_id=%s",
            (nome, empresa, interesse, contato, lead_id, session['usuario_id'])
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao editar lead: {e}")
        
    return redirect(url_for('base_leads'))

@app.route('/deletar_lead', methods=['POST'])
def deletar_lead():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    
    lead_id = request.form.get('lead_id')
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute("DELETE FROM leads WHERE id=%s AND usuario_id=%s", (lead_id, session['usuario_id']))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao deletar lead: {e}")
        
    return redirect(url_for('base_leads'))

@app.route('/adicionar_nota', methods=['POST'])
def adicionar_nota():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    
    lead_id = request.form.get('lead_id')
    nova_nota = request.form.get('nova_nota')
    
    if nova_nota:
        try:
            conn = conectar_banco()
            cur = conn.cursor()
            cur.execute("INSERT INTO notas_leads (lead_id, nota) VALUES (%s, %s)", (lead_id, nova_nota[:300]))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Erro ao adicionar nota: {e}")
            
    return redirect(url_for('base_leads'))

if __name__ == '__main__':
    app.run(debug=True)