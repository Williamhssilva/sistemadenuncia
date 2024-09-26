from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import logging
from sqlalchemy.orm import joinedload

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)

template_dir = os.path.abspath('app/templates')
static_dir = os.path.abspath('app/static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Configuração do banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'denuncias.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

@app.route('/')
def index():
    return render_template('index.html')

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
def dashboard():
    denuncias = Denuncia.query.options(joinedload('*')).all()
    denuncias_dict = []
    for denuncia in denuncias:
        denuncia_dict = denuncia.to_dict()
        denuncia_dict['data_criacao'] = denuncia.data_criacao
        denuncia_dict['data_ocorrencia'] = denuncia.data_ocorrencia
        denuncias_dict.append(denuncia_dict)

    total_denuncias = len(denuncias_dict)
    
    categorias = {}
    status = {}
    
    for denuncia in denuncias_dict:
        categorias[denuncia['categoria']] = categorias.get(denuncia['categoria'], 0) + 1
        status[denuncia['status']] = status.get(denuncia['status'], 0) + 1
    
    # Converter para porcentagens
    for cat in categorias:
        categorias[cat] = round((categorias[cat] / total_denuncias) * 100, 2) if total_denuncias > 0 else 0
    
    for st in status:
        status[st] = round((status[st] / total_denuncias) * 100, 2) if total_denuncias > 0 else 0
    
    return render_template('dashboard.html', denuncias=denuncias_dict, total_denuncias=total_denuncias, categorias=categorias, status=status)

@app.route('/denuncia/<int:id>')
def get_denuncia(id):
    denuncia = Denuncia.query.get_or_404(id)
    return jsonify(denuncia.to_dict())

@app.route('/atualizar_status/<int:id>', methods=['POST'])
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
def get_denuncias():
    denuncias = Denuncia.query.all()
    return jsonify([denuncia.to_dict() for denuncia in denuncias])

@app.route('/get_dashboard_data')
def get_dashboard_data():
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
        'denuncias': [denuncia.to_dict() for denuncia in denuncias]
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)