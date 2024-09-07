from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime
from meteostat import Point, Daily

app = Flask(__name__)

API_KEY = '5a7c62364e30c5c1434e932687b0dfb6'

def avaliar_condicoes_climaticas(temperatura, umidade):
    recomendacoes = []

    # Regras para Milho
    if 20 <= temperatura <= 30 and 50 <= umidade <= 70:
        recomendacoes.append("As condições estão boas para o cultivo de milho.")

    # Regras para Trigo
    if 10 <= temperatura <= 25 and 40 <= umidade <= 60:
        recomendacoes.append("As condições estão boas para o cultivo de trigo.")

    # Regras para Soja
    if 20 <= temperatura <= 30 and 60 <= umidade <= 80:
        recomendacoes.append("As condições estão boas para o cultivo de soja.")

    if not recomendacoes:
        recomendacoes.append("As condições atuais não são ideais para milho, trigo ou soja.")
    
    return recomendacoes

def avaliar_previsao(previsao):
    dias_ideais = []
    for dia in previsao['list']:
        temperatura = dia['main']['temp']
        umidade = dia['main']['humidity']
        data = dia['dt_txt']
        recomendacoes = avaliar_condicoes_climaticas(temperatura, umidade)
        print(f"Verificando {data}: Temp={temperatura}, Umidade={umidade}, Recomendações={recomendacoes}")
        if "As condições estão boas para o cultivo de" in recomendacoes[0]:
            dias_ideais.append(f"Data: {data}, Condições: {recomendacoes[0]}")

    if not dias_ideais:
        dias_ideais.append("Nenhum dia ideal foi encontrado nos próximos dias com base na previsão.")

    return dias_ideais

def obter_dados_historicos(lat, lon):
    # Configurar o ponto para os dados históricos (latitude, longitude)
    location = Point(lat, lon)
    
    # Obter dados diários para o mês de agosto dos últimos 5 anos
    start = datetime(datetime.now().year - 5, 8, 1)
    end = datetime(datetime.now().year, 8, 31)
    data = Daily(location, start, end)
    data = data.fetch()

    return data

def analisar_dados_historicos(dados_historicos):
    # Análise simples para determinar o período ideal
    dias_ideais = []
    
    # Vamos supor que estamos analisando a temperatura média para simplicidade
    for index, row in dados_historicos.iterrows():
        if 20 <= row['tavg'] <= 30:  # Exemplo de condição ideal para temperatura média
            dias_ideais.append(index.strftime('%Y-%m-%d'))
    
    return dias_ideais

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/obter_clima', methods=['POST'])
def obter_clima():
    cidade = request.form.get('cidade', '').strip()
    if not cidade:
        return render_template('index.html', clima=None, message="Por favor, insira o nome de uma cidade válida.")

    url_atual = f'https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={API_KEY}&units=metric&lang=pt_br'
    url_previsao = f'https://api.openweathermap.org/data/2.5/forecast?q={cidade}&appid={API_KEY}&units=metric&lang=pt_br'

    try:
        response_atual = requests.get(url_atual)
        response_previsao = requests.get(url_previsao)
        response_atual.raise_for_status()
        response_previsao.raise_for_status()
        dados_atual = response_atual.json()
        dados_previsao = response_previsao.json()
    except requests.exceptions.RequestException:
        return render_template('index.html', clima=None, message="Erro na conexão com a API do OpenWeather.")
    except ValueError:
        return render_template('index.html', clima=None, message="Resposta inválida da API do OpenWeather.")

    if dados_atual.get("cod") != 200:
        clima = None
        mensagem = dados_atual.get("message", "Erro ao obter dados climáticos.")
    else:
        temperatura = dados_atual["main"].get("temp")
        umidade = dados_atual["main"].get("humidity")
        lat = dados_atual['coord']['lat']
        lon = dados_atual['coord']['lon']

        clima = {
            "cidade": dados_atual.get("name"),
            "temperatura": temperatura,
            "descricao": dados_atual["weather"][0].get("description"),
            "umidade": umidade,
            "velocidade_vento": dados_atual["wind"].get("speed")
        }
        recomendacoes = avaliar_condicoes_climaticas(temperatura, umidade)
        dias_ideais = avaliar_previsao(dados_previsao)
        
        # Obter e analisar dados históricos
        dados_historicos = obter_dados_historicos(lat, lon)
        dias_historicos_ideais = analisar_dados_historicos(dados_historicos)
        
        mensagem = None

    return render_template('index.html', clima=clima, message=mensagem, recomendacoes=recomendacoes, dias_ideais=dias_ideais, dias_historicos_ideais=dias_historicos_ideais)

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query', '')
    if query:
        url = f'https://api.openweathermap.org/data/2.5/find?q={query}&type=like&appid={API_KEY}&limit=5&units=metric&lang=pt_br'
        response = requests.get(url)
        results = response.json()
        cities = []
        if results.get('list'):
            for item in results['list']:
                city_name = item['name']
                country = item['sys']['country']
                state = item.get('state')  # Para países como EUA que retornam 'state'
                if state:
                    city_display = f"{city_name} - {state}, {country}"
                else:
                    city_display = f"{city_name}, {country}"
                cities.append(city_display)
        return jsonify(cities)
    return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)
