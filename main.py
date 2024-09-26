from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import logging
from sqlalchemy.orm import joinedload

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)

template_dir = os.path.abspath('app/templates')
static_dir = os.path.abspath('app/static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'  # Mude isso para uma chave secreta real

# Configuração do banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'denuncias.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Denuncia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conteudo = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    local = db.Column(db.String(100))
    data_ocorrencia = db.Column(db.Date)
    status = db.Column(db.String(20), default='Em análise')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    STATUS_CHOICES = ['Em análise', 'Em andamento', 'Concluída', 'Arquivada']

    def to_dict(self):
        return {
            'id': self.id,
            'conteudo': self.conteudo,
            'categoria': self.categoria,
            'local': self.local,
            'data_ocorrencia': self.data_ocorrencia.isoformat() if self.data_ocorrencia else None,
            'status': self.status,
            'data_criacao': self.data_criacao.isoformat()
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de denúncias por página
    denuncias = Denuncia.query.order_by(Denuncia.data_criacao.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('index.html', denuncias=denuncias)

@app.route('/denunciar', methods=['POST'])
def criar_denuncia():
    try:
        dados = request.json
        logging.debug(f"Dados recebidos: {dados}")
        nova_denuncia = Denuncia(
            conteudo=dados['conteudo'],
            categoria=dados['categoria'],
            local=dados['local'],
            data_ocorrencia=datetime.strptime(dados['data_ocorrencia'], '%Y-%m-%d').date() if dados['data_ocorrencia'] else None
        )
        db.session.add(nova_denuncia)
        db.session.commit()
        return jsonify(nova_denuncia.to_dict()), 201
    except Exception as e:
        logging.error(f"Erro ao criar denúncia: {str(e)}")
        db.session.rollback()
        print(f"Erro ao criar denúncia: {str(e)}")
        return jsonify({"error": "Erro ao processar a denúncia"}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de denúncias por página
    denuncias = Denuncia.query.order_by(Denuncia.data_criacao.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    total_denuncias = Denuncia.query.count()
    
    categorias = db.session.query(Denuncia.categoria, db.func.count(Denuncia.id)).group_by(Denuncia.categoria).all()
    categorias = {categoria: count for categoria, count in categorias}
    
    status = db.session.query(Denuncia.status, db.func.count(Denuncia.id)).group_by(Denuncia.status).all()
    status = {s: count for s, count in status}
    
    return render_template('dashboard.html', denuncias=denuncias, total_denuncias=total_denuncias, categorias=categorias, status=status)

@app.route('/denuncia/<int:id>')
@login_required
def get_denuncia(id):
    denuncia = Denuncia.query.get_or_404(id)
    return jsonify(denuncia.to_dict())

@app.route('/atualizar_status/<int:id>', methods=['POST'])
@login_required
def atualizar_status(id):
    denuncia = Denuncia.query.get_or_404(id)
    novo_status = request.json.get('status')
    if novo_status in Denuncia.STATUS_CHOICES:
        denuncia.status = novo_status
        db.session.commit()
        return jsonify(denuncia.to_dict()), 200
    else:
        return jsonify({"error": "Status inválido"}), 400

@app.route('/get_denuncias')
@login_required
def get_denuncias():
    denuncias = Denuncia.query.all()
    return jsonify([denuncia.to_dict() for denuncia in denuncias])

@app.route('/get_dashboard_data')
@login_required
def get_dashboard_data():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de denúncias por página
    denuncias_paginadas = Denuncia.query.order_by(Denuncia.data_criacao.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    denuncias = Denuncia.query.all()
    total_denuncias = len(denuncias)
    
    categorias = {}
    status = {}
    denuncias_por_dia = {}
    
    # Inicializa os últimos 30 dias com 0 denúncias
    hoje = datetime.now().date()
    for i in range(30, -1, -1):  # Alterado para incluir hoje (-1)
        data = (hoje - timedelta(days=i)).strftime('%Y-%m-%d')
        denuncias_por_dia[data] = 0
    
    for denuncia in denuncias:
        categorias[denuncia.categoria] = categorias.get(denuncia.categoria, 0) + 1
        status[denuncia.status] = status.get(denuncia.status, 0) + 1
        
        data = denuncia.data_criacao.strftime('%Y-%m-%d')
        denuncias_por_dia[data] = denuncias_por_dia.get(data, 0) + 1
    
    # Converter para porcentagens
    for cat in categorias:
        categorias[cat] = (categorias[cat] / total_denuncias) * 100
    
    for st in status:
        status[st] = (status[st] / total_denuncias) * 100
    
    return jsonify({
        'total_denuncias': total_denuncias,
        'categorias': categorias,
        'status': status,
        'denuncias_por_dia': denuncias_por_dia,
        'denuncias': [denuncia.to_dict() for denuncia in denuncias_paginadas.items],
        'total_pages': denuncias_paginadas.pages,
        'current_page': page
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Crie um usuário de teste se não existir
        if not User.query.filter_by(username='admin').first():
            hashed_password = generate_password_hash('senha123')
            new_user = User(username='admin', password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
    app.run(debug=True)
    
    from app import app, db, Denuncia