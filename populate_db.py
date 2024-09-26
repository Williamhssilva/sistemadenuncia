import sys
import os

# Adiciona o diretório atual ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Importa os objetos necessários
from main import app, db, Denuncia

from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker('pt_BR')

# Categorias disponíveis
categorias = ['Corrupção', 'Assédio', 'Fraude', 'Discriminação', 'Outros']

# Status disponíveis
status_list = ['Em análise', 'Em andamento', 'Concluída', 'Arquivada']

def create_fake_denuncia():
    return Denuncia(
        conteudo=fake.text(max_nb_chars=500),
        categoria=random.choice(categorias),
        local=fake.city(),
        data_ocorrencia=fake.date_between(start_date='-1y', end_date='today'),
        status=random.choice(status_list),
        data_criacao=fake.date_time_between(start_date='-1y', end_date='now')
    )

def populate_database(num_denuncias=200):
    with app.app_context():
        for _ in range(num_denuncias):
            denuncia = create_fake_denuncia()
            db.session.add(denuncia)
        
        db.session.commit()
        print(f"{num_denuncias} denúncias de teste foram adicionadas ao banco de dados.")

if __name__ == '__main__':
    populate_database()