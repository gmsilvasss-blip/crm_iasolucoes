import os
import json
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_desenvolvimento")
DATABASE_URL = os.getenv("DATABASE_URL")

def conectar_banco(): return psycopg2.connect(DATABASE_URL)

# ==========================================
# MÓDULO: AUTENTICAÇÃO
# ==========================================
@app.route('/')
def inicio():
    if 'usuario_id' in session: return redirect(url_for('home'))
    return render_template('inicio.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email'); senha = request.form.get('senha')
        try:
            conn = conectar_banco(); cur = conn.cursor()
            cur.execute("SELECT id, senha_hash FROM usuarios WHERE email = %s", (email,))
            usuario = cur.fetchone(); cur.close(); conn.close()
            if usuario and check_password_hash(usuario[1], senha):
                session['usuario_id'] = usuario[0]
                return redirect(url_for('home'))
            return "<h1>Erro de Login</h1>", 401
        except Exception as e: return f"Erro: {e}", 500
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form.get('email'); telefone = request.form.get('telefone'); senha = generate_password_hash(request.form.get('senha'))
        token = secrets.token_hex(8) # Gera token único para o link de captura
        try:
            conn = conectar_banco(); cur = conn.cursor()
            cur.execute("INSERT INTO usuarios (email, telefone, senha_hash, token_publico) VALUES (%s, %s, %s, %s)", (email, telefone, senha, token))
            conn.commit(); cur.close(); conn.close()
            return redirect(url_for('login'))
        except Exception as e: return f"Erro: {e}", 500
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.pop('usuario_id', None); return redirect(url_for('inicio'))

# ==========================================
# MÓDULO: AGENDA E DASHBOARD
# ==========================================
@app.route('/home')
def home():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    proximo_compromisso = None; eventos_calendario = []; lista_leads = []
    pipeline = {'Qualificação': 0, 'Negociação': 0, 'Fechado': 0, 'Perdido': 0}
    try:
        conn = conectar_banco(); cur = conn.cursor()
        
        # Próximo Compromisso
        cur.execute("SELECT titulo_compromisso, data_hora FROM agenda WHERE usuario_id = %s AND data_hora >= CURRENT_TIMESTAMP AND status = 'Pendente' ORDER BY data_hora ASC LIMIT 1", (session['usuario_id'],))
        resultado = cur.fetchone()
        if resultado: proximo_compromisso = f"{resultado[1].strftime('%H:%M')} - {resultado[0]}"
            
        # Agenda
        cur.execute("SELECT id, titulo_compromisso, data_hora, status, observacoes, lead_id FROM agenda WHERE usuario_id = %s", (session['usuario_id'],))
        for t in cur.fetchall():
            eventos_calendario.append({"id": t[0], "titulo": t[1], "data": t[2].strftime('%Y-%m-%d'), "hora": t[2].strftime('%H:%M'), "status": t[3], "obs": t[4] if t[4] else "", "lead_id": t[5] if t[5] else ""})
            
        # Pipeline (Caixas D'água)
        cur.execute("SELECT status, COUNT(*) FROM leads WHERE usuario_id = %s GROUP BY status", (session['usuario_id'],))
        for stat, count in cur.fetchall():
            if stat in pipeline: pipeline[stat] = count
            
        # Lista Leads p/ Modal Agenda
        cur.execute("SELECT id, nome, empresa FROM leads WHERE usuario_id = %s ORDER BY nome ASC", (session['usuario_id'],))
        lista_leads = [{"id": l[0], "nome": l[1], "empresa": l[2]} for l in cur.fetchall()]
            
        cur.close(); conn.close()
    except Exception as e: print(f"Erro BD Home: {e}")
    return render_template('home.html', compromisso=proximo_compromisso, eventos_json=json.dumps(eventos_calendario), leads=lista_leads, pipeline=pipeline)

@app.route('/minha_agenda', methods=['POST'])
def minha_agenda():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    valor_select = request.form.get('titulo_compromisso')
    data_str = request.form.get('data_compromisso'); hora_str = request.form.get('hora_compromisso') 
    nota_agendamento = request.form.get('nota_agendamento'); data_hora_completa = f"{data_str} {hora_str}:00"
    lead_id = None; titulo = valor_select
    if '|' in valor_select: partes = valor_select.split('|', 1); lead_id = partes[0]; titulo = partes[1]
    
    try:
        conn = conectar_banco(); cur = conn.cursor()
        cur.execute("INSERT INTO agenda (usuario_id, titulo_compromisso, data_hora, status, lead_id, observacoes) VALUES (%s, %s, %s, 'Pendente', %s, %s)", (session['usuario_id'], titulo, data_hora_completa, lead_id, nota_agendamento))
        if lead_id: cur.execute("INSERT INTO notas_leads (lead_id, nota) VALUES (%s, %s)", (lead_id, f"[Agendado para {data_str} às {hora_str}] {nota_agendamento if nota_agendamento else ''}"[:300]))
        conn.commit(); cur.close(); conn.close()
    except: pass
    return redirect(url_for('home'))

@app.route('/salvar_feedback', methods=['POST'])
def salvar_feedback():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    evento_id = request.form.get('evento_id'); lead_id = request.form.get('lead_id'); observacoes = request.form.get('observacoes'); acao = request.form.get('acao') 
    try:
        conn = conectar_banco(); cur = conn.cursor(); prefixo = ""
        if acao == 'excluir': cur.execute("DELETE FROM agenda WHERE id = %s AND usuario_id = %s", (evento_id, session['usuario_id'])); prefixo = "[Cancelado/Excluído]"
        elif acao == 'reagendar': 
            nova_data = request.form.get('data_compromisso'); nova_hora = request.form.get('hora_compromisso')
            cur.execute("UPDATE agenda SET observacoes = %s, status = 'Pendente', data_hora = %s WHERE id = %s AND usuario_id = %s", (observacoes, f"{nova_data} {nova_hora}:00", evento_id, session['usuario_id'])); prefixo = f"[Reagendado para {nova_data} às {nova_hora}]"
        else: cur.execute("UPDATE agenda SET observacoes = %s, status = 'Concluído' WHERE id = %s AND usuario_id = %s", (observacoes, evento_id, session['usuario_id'])); prefixo = "[Concluído]"
        if lead_id and lead_id != "None": cur.execute("INSERT INTO notas_leads (lead_id, nota) VALUES (%s, %s)", (lead_id, f"{prefixo} {observacoes}"[:300]))
        conn.commit(); cur.close(); conn.close()
    except: pass
    return redirect(url_for('home'))

# ==========================================
# MÓDULO: BASE DE LEADS E PRODUTOS
# ==========================================
@app.route('/base_leads')
def base_leads():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    leads_processados = []; produtos = []; token_publico = ""
    try:
        conn = conectar_banco(); cur = conn.cursor()
        
        # Pega Token do Vendedor
        cur.execute("SELECT token_publico FROM usuarios WHERE id = %s", (session['usuario_id'],))
        token_publico = cur.fetchone()[0]
        
        # Pega Produtos Cadastrados
        cur.execute("SELECT id, nome, descricao FROM produtos WHERE usuario_id = %s ORDER BY nome ASC", (session['usuario_id'],))
        produtos = [{"id": p[0], "nome": p[1], "desc": p[2]} for p in cur.fetchall()]
        
        # Pega Leads
        cur.execute("SELECT id, nome, empresa, interesse, telefone, email, endereco, status FROM leads WHERE usuario_id = %s ORDER BY id DESC", (session['usuario_id'],))
        for l in cur.fetchall():
            lead_id = l[0]
            cur.execute("SELECT nota, data_criacao FROM notas_leads WHERE lead_id = %s ORDER BY data_criacao DESC", (lead_id,))
            lista_notas = [{"texto": n[0], "data": n[1].strftime('%d/%m %H:%M')} for n in cur.fetchall()]
            leads_processados.append({"id": lead_id, "nome": l[1], "empresa": l[2], "interesse": l[3], "telefone": l[4], "email": l[5], "endereco": l[6], "status": l[7], "notas": lista_notas})
            
        cur.close(); conn.close()
    except Exception as e: print(f"Erro Base Leads: {e}")
    return render_template('base_leads.html', leads=leads_processados, produtos=produtos, token=token_publico)

@app.route('/cadastrar_lead', methods=['POST'])
def cadastrar_lead():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    nome = request.form.get('nome'); empresa = request.form.get('empresa'); interesse = request.form.get('interesse')
    telefone = request.form.get('telefone'); email = request.form.get('email'); endereco = request.form.get('endereco'); status = request.form.get('status')
    try:
        conn = conectar_banco(); cur = conn.cursor()
        cur.execute("INSERT INTO leads (usuario_id, nome, empresa, interesse, telefone, email, endereco, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id", (session['usuario_id'], nome, empresa, interesse, telefone, email, endereco, status))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(e)
    return redirect(url_for('base_leads'))

@app.route('/editar_lead', methods=['POST'])
def editar_lead():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    lead_id = request.form.get('lead_id'); nome = request.form.get('nome'); empresa = request.form.get('empresa'); interesse = request.form.get('interesse')
    telefone = request.form.get('telefone'); email = request.form.get('email'); endereco = request.form.get('endereco'); status = request.form.get('status')
    try:
        conn = conectar_banco(); cur = conn.cursor()
        cur.execute("UPDATE leads SET nome=%s, empresa=%s, interesse=%s, telefone=%s, email=%s, endereco=%s, status=%s WHERE id=%s AND usuario_id=%s", (nome, empresa, interesse, telefone, email, endereco, status, lead_id, session['usuario_id']))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(e)
    return redirect(url_for('base_leads'))

@app.route('/adicionar_nota', methods=['POST'])
def adicionar_nota():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    lead_id = request.form.get('lead_id'); nova_nota = request.form.get('nova_nota')
    if nova_nota:
        try:
            conn = conectar_banco(); cur = conn.cursor()
            cur.execute("INSERT INTO notas_leads (lead_id, nota) VALUES (%s, %s)", (lead_id, nova_nota[:300]))
            conn.commit(); cur.close(); conn.close()
        except: pass
    return redirect(url_for('base_leads'))

@app.route('/adicionar_produto', methods=['POST'])
def adicionar_produto():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    nome = request.form.get('nome'); descricao = request.form.get('descricao')
    try:
        conn = conectar_banco(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM produtos WHERE usuario_id = %s", (session['usuario_id'],))
        if cur.fetchone()[0] >= 20: return "<h1>Limite de 20 produtos atingido. Exclua algum para adicionar novos.</h1>", 400
        cur.execute("INSERT INTO produtos (usuario_id, nome, descricao) VALUES (%s, %s, %s)", (session['usuario_id'], nome, descricao))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(e)
    return redirect(url_for('base_leads'))

@app.route('/deletar_produto', methods=['POST'])
def deletar_produto():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    produto_id = request.form.get('produto_id')
    try:
        conn = conectar_banco(); cur = conn.cursor()
        cur.execute("DELETE FROM produtos WHERE id = %s AND usuario_id = %s", (produto_id, session['usuario_id']))
        conn.commit(); cur.close(); conn.close()
    except: pass
    return redirect(url_for('base_leads'))

# ==========================================
# MÓDULO: CAPTURA PÚBLICA (LINK EXTERNO)
# ==========================================
@app.route('/captura/<token>', methods=['GET'])
def captura_publica(token):
    try:
        conn = conectar_banco(); cur = conn.cursor()
        # Acha o vendedor dono do link
        cur.execute("SELECT id FROM usuarios WHERE token_publico = %s", (token,))
        vendedor = cur.fetchone()
        if not vendedor: return "<h1>Link inválido ou expirado.</h1>", 404
        
        vendedor_id = vendedor[0]
        # Pega os produtos desse vendedor para exibir no formulário
        cur.execute("SELECT nome FROM produtos WHERE usuario_id = %s ORDER BY nome ASC", (vendedor_id,))
        produtos = [p[0] for p in cur.fetchall()]
        cur.close(); conn.close()
        return render_template('captura.html', token=token, produtos=produtos)
    except: return "Erro ao carregar página", 500

@app.route('/captura_submit/<token>', methods=['POST'])
def captura_submit(token):
    try:
        conn = conectar_banco(); cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE token_publico = %s", (token,))
        vendedor = cur.fetchone()
        if not vendedor: return "Erro", 404
        
        nome = request.form.get('nome'); empresa = request.form.get('empresa'); interesse = request.form.get('interesse')
        telefone = request.form.get('telefone'); email = request.form.get('email'); endereco = request.form.get('endereco')
        status = 'Qualificação' # Entra no funil automático
        
        cur.execute("INSERT INTO leads (usuario_id, nome, empresa, interesse, telefone, email, endereco, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id", (vendedor[0], nome, empresa, interesse, telefone, email, endereco, status))
        novo_lead_id = cur.fetchone()[0]
        
        # Insere a nota inicial automática
        cur.execute("INSERT INTO notas_leads (lead_id, nota) VALUES (%s, %s)", (novo_lead_id, "[Captura Pública] Lead auto-cadastrado via Link online."))
        
        conn.commit(); cur.close(); conn.close()
        return "<h1>Sucesso! Seus dados foram enviados.</h1><p>Nossa equipe entrará em contato em breve.</p>"
    except Exception as e: return f"Erro: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)