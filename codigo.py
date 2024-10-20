from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Configuração do banco de dados SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cavalos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar o banco de dados
db = SQLAlchemy(app)


# Definir a classe do modelo de dados
class Cavalo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    resultados = db.relationship('Resultado', backref='cavalo', lazy=True, cascade='all, delete-orphan')


class Resultado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tempo = db.Column(db.String(50), nullable=False)
    data = db.Column(db.String(50), nullable=False, default=datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    cavalo_id = db.Column(db.Integer, db.ForeignKey('cavalo.id'), nullable=False)
    competicao = db.Column(db.String(100), nullable=True)  # Competição pode ser nula em treinamentos
    tipo = db.Column(db.String(20), nullable=False)  # 'treinamento' ou 'competicao'
    faltas = db.Column(db.Integer, nullable=False, default=0)  # Número de faltas

# Função para salvar resultado de treinamento
def salvar_resultado_treinamento(cavalo_id, tempo):
    novo_resultado = Resultado(
        tempo=tempo,
        cavalo_id=cavalo_id,
        competicao=None,  # Em treinamento, a competição é None
        tipo='treinamento'  # Define o tipo como 'treinamento'
    )
    db.session.add(novo_resultado)
    db.session.commit()


# Função para salvar resultado de competição
def salvar_resultado_competicao(cavalo_id, tempo, competicao, faltas):
    novo_resultado = Resultado(
        tempo=tempo,
        cavalo_id=cavalo_id,
        competicao=competicao,  # Nome da competição
        tipo='competicao',  # Define o tipo como 'competicao'
        faltas=faltas  # Número de faltas
    )
    db.session.add(novo_resultado)
    db.session.commit()





# Exibir resultados de treinamentos anteriores
@app.route('/resultados')
def exibir_resultados():
    cavalos = Cavalo.query.all()
    resultados = {}
    for cavalo in cavalos:
        resultados[cavalo.nome] = Resultado.query.filter_by(cavalo_id=cavalo.id, tipo='treinamento').all()
    return render_template('resultados.html', resultados=resultados)


@app.route('/competicoesanteriores')
def competicoesanteriores():
    # Recupera todas as competições distintas que estão presentes na tabela de resultados
    competicoes = db.session.query(Resultado.competicao).filter(Resultado.tipo == 'competicao',
                                                                Resultado.competicao.isnot(None)).distinct().all()

    competicoes_dict = {}

    # Para cada competição distinta, busca os resultados associados
    for competicao in competicoes:
        if competicao[0]:  # Verifica se há uma competição válida
            resultados = Resultado.query.filter_by(competicao=competicao[0], tipo='competicao').all()

            # Ordenar resultados pelo tempo (convertendo para milissegundos para comparação)
            resultados_ordenados = sorted(resultados, key=lambda r: converte_tempo_para_milissegundos(r.tempo))

            competicoes_dict[competicao[0]] = resultados_ordenados

    return render_template('competicoesanteriores.html', competicoes=competicoes_dict)

# Função para converter o tempo de string para milissegundos
def converte_tempo_para_milissegundos(tempo_str):
    minutos, segundos, milissegundos = map(int, tempo_str.split(":"))
    total_milissegundos = (minutos * 60 * 1000) + (segundos * 1000) + milissegundos
    return total_milissegundos



# Rota para salvar o resultado de um treinamento
@app.route('/salvar_resultado/<string:tempo>/<string:cavalo_nome>')
def salvar_resultado(tempo, cavalo_nome):
    cavalo = Cavalo.query.filter_by(nome=cavalo_nome).first()
    if cavalo:
        # Salvando resultado de treinamento
        salvar_resultado_treinamento(cavalo.id, tempo)
    return redirect(url_for('exibir_resultados'))


# Rota para salvar o resultado de uma competição
@app.route('/salvar_resultado_competicao/<int:cavalo_id>/<string:tempo>/<int:faltas>/<string:competicao_nome>', methods=['POST'])
def salvar_resultado_competicao_route(cavalo_id, tempo, faltas, competicao_nome):
    cavalo = Cavalo.query.get(cavalo_id)
    if cavalo:
        salvar_resultado_competicao(cavalo_id, tempo, competicao_nome, faltas)
    return '', 200


@app.route('/verificar_nome_competicao/<string:nome_competicao>', methods=['GET'])
def verificar_nome_competicao(nome_competicao):
    # Verifica se já existe algum resultado com o nome dessa competição
    competicao_existente = Resultado.query.filter_by(competicao=nome_competicao).first()

    if competicao_existente:
        return {'error': 'Nome de competição já em uso. Escolha outro nome ou exclua a competição já existente em Competições Anteriores'}, 400
    return {'message': 'Nome disponível'}, 200


@app.route('/competicao')
def competicao():
    cavalos = Cavalo.query.all()
    return render_template('competicao.html', cavalos=cavalos)


@app.route('/adicionar_cavalo', methods=['GET', 'POST'])
def adicionar_cavalo():
    if request.method == 'POST':
        novo_cavalo = request.form['novo_cavalo']
        if novo_cavalo and not Cavalo.query.filter_by(nome=novo_cavalo).first():
            cavalo = Cavalo(nome=novo_cavalo)
            db.session.add(cavalo)
            db.session.commit()
            return redirect(url_for('adicionar_cavalo'))
    cavalos = Cavalo.query.all()
    return render_template('adicionar_cavalo.html', cavalos=cavalos)


@app.route('/remover_cavalo/<int:cavalo_id>', methods=['POST'])
def remover_cavalo(cavalo_id):
    cavalo = Cavalo.query.get_or_404(cavalo_id)
    db.session.delete(cavalo)
    db.session.commit()
    return redirect(url_for('adicionar_cavalo'))


@app.route('/excluir_resultado/<int:resultado_id>', methods=['POST'])
def excluir_resultado(resultado_id):
    resultado = Resultado.query.get_or_404(resultado_id)
    db.session.delete(resultado)
    db.session.commit()
    return redirect(url_for('exibir_resultados'))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/cronometroinicial')
def cronometroinicial():
    return render_template('cronometroinicial.html')


@app.route('/cronometro')
def cronometro():
    cavalos = Cavalo.query.all()
    return render_template('cronometro.html', cavalos=cavalos)

@app.route('/excluir_resultado_competicao/<int:resultado_id>', methods=['POST'])
def excluir_resultado_competicao(resultado_id):
    resultado = Resultado.query.get_or_404(resultado_id)
    db.session.delete(resultado)
    db.session.commit()
    return redirect(url_for('competicoesanteriores'))


@app.route('/adicionar_varios_cavalos', methods=['POST'])
def adicionar_varios_cavalos():
    nomes_cavalos = request.form['nomes_cavalos']

    # Quebra a entrada em várias linhas
    lista_nomes = nomes_cavalos.splitlines()

    # Para cada nome, cria um novo cavalo no banco de dados
    for nome in lista_nomes:
        nome = nome.strip()  # Remove espaços em branco extras
        if nome and not Cavalo.query.filter_by(nome=nome).first():
            cavalo = Cavalo(nome=nome)
            db.session.add(cavalo)

    db.session.commit()

    return redirect(url_for('adicionar_cavalo'))

@app.route('/excluir_todos_cavalos', methods=['POST'])
def excluir_todos_cavalos():
    db.session.query(Cavalo).delete()  # Exclui todos os cavalos
    db.session.commit()
    return redirect(url_for('adicionar_cavalo'))  # Redireciona para a página de gerenciamento



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
