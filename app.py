import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import numpy as np
measures = {
    "LED": {"cost": 15, "effect": 0.08, "color":"#FFD700"},
    "Утеплення": {"cost": 25, "effect": 0.15, "color":"#FF4500"},
    "Solar": {"cost": 30, "effect": 0.20, "color":"#1E90FF"},
    "Smart_meter": {"cost": 10, "effect": 0.05, "color":"#32CD32"},
    "Smart_home": {"cost": 6, "effect": 0.03, "color":"#FF69B4"}
}
budget_per_year_default = 100
climate_plan = {
    "Помірний": {1: ["LED", "Утеплення", "Solar"], 2: ["Solar"], 5: ["Smart_meter", "Smart_home"]},
    "Дуже холодний": {1: ["LED", "Утеплення"], 2: ["Утеплення"], 5: ["Smart_meter", "Smart_home"]},
    "Сонячний": {1: ["LED", "Solar"], 2: ["Solar"], 5: ["Smart_meter", "Smart_home"]},
    "Змішаний": {1: ["LED", "Утеплення", "Solar"], 2: ["Solar"], 5: ["Smart_meter", "Smart_home"]}
}

def simulate_energy(buildings, budget, climate, price_per_mwh=1):
    base_yearly = sum(buildings[b]["count"]*buildings[b]["consumption"]*12 for b in buildings)
    yearly_consumption = []
    plan_per_year = []
    
    remaining_budget = budget
    current_consumption = base_yearly
    
    for year in range(1, 11):
        # Вибір заходів
        if year == 1:
            active_measures = climate_plan[climate][1]
        elif 2 <= year <= 4:
            active_measures = climate_plan[climate][2]
        else:
            active_measures = climate_plan[climate][5]

        # Рахуємо вартість та масштабуємо під доступний бюджет
        total_cost = sum([measures[m]["cost"] for m in active_measures])
        scale = min(1, remaining_budget / total_cost)

        # Ефект заходів
        multiplier = np.prod([1 - measures[m]["effect"]*scale for m in active_measures])
        new_consumption = current_consumption * multiplier
        
        # Таблиця заходів
        plan_per_year.append([{
            "name": m, 
            "effect": measures[m]["effect"]*scale, 
            "color": measures[m]["color"]
        } for m in active_measures])

        yearly_consumption.append(new_consumption)
        saved_energy = (current_consumption - new_consumption)  
        saved_budget = saved_energy * price_per_mwh / 1e6  
        
        # Наступний рік
        remaining_budget = budget + saved_budget
        current_consumption = new_consumption

    return yearly_consumption, plan_per_year

app = dash.Dash(__name__)
app.title = "Міський енергетичний графік"

app.layout = html.Div([
    html.H1("Міський Енергетичний План", style={'textAlign': 'center', "color": "limegreen"}),
    
    html.Div([
        html.Label("Оберіть клімат міста:"),
        dcc.Dropdown(
            id='climate-selector',
            options=[{'label': k, 'value': k} for k in climate_plan.keys()],
            value='Помірний'
        ),
        html.Br(),
        html.Label("Кількість квартир:"),
        dcc.Input(id='apartments', type='number', value=40000, min=0, step=100),
        html.Br(),
        html.Label("Кількість приватних будинків:"),
        dcc.Input(id='houses', type='number', value=5000, min=0, step=10),
        html.Br(),
        html.Label("Кількість громадських будівель:"),
        dcc.Input(id='public', type='number', value=300, min=0, step=1),
        html.Br(),
        html.Label("Бюджет міста на рік:"),
        dcc.Input(id='budget', type='number', value=budget_per_year_default, min=0, step=1),
        html.Br(), html.Br(),
        html.Button("Розрахувати план", id="run-button", n_clicks=0)
    ], style={'margin': '20px'}),
    
    dcc.Graph(id='consumption-graph'),
    
    html.H2("Таблиця споживання по роках"),
    html.Div(id='table-container'),
    
    html.H2("План енергозбереження по роках"),
    html.Div(id='plan-container')
])

@app.callback(
    Output('consumption-graph', 'figure'),
    Output('table-container', 'children'),
    Output('plan-container', 'children'),
    Input('run-button', 'n_clicks'),
    State('climate-selector', 'value'),
    State('apartments', 'value'),
    State('houses', 'value'),
    State('public', 'value'),
    State('budget', 'value')
)
def update_graph(n_clicks, climate, apartments, houses, public, budget):
    buildings = {
        "Квартири": {"count": apartments, "consumption": 250},
        "Приватні будинки": {"count": houses, "consumption": 400},
        "Громадські будівлі": {"count": public, "consumption": 3000}
    }
    
    cons, plan = simulate_energy(buildings, budget, climate)
    
    # Графік з анімацією та економією
    fig = go.Figure()
    years = np.arange(1, 11)
    base = sum(buildings[b]["count"]*buildings[b]["consumption"]*12 for b in buildings)/1e6
    
    # Лінія споживання 
    fig.add_trace(go.Scatter(
        x=years, y=np.array(cons)/1e6,
        mode='lines+markers',
        name='Споживання міста',
        line=dict(color='limegreen', width=4)
    ))
    fig.update_layout(
        title="Прогноз споживання електроенергії на 10 років",
        xaxis_title="Рік",
        yaxis_title="Споживання (млн кВт·год)",
        template="plotly_dark",
        height=600
    )
    
    # Таблиця споживання
    table = html.Table([html.Tr([html.Th("Рік"), html.Th("Споживання (млн кВт·год)")])] + [
        html.Tr([html.Td(year), html.Td(f"{c/1e6:.2f}")])
        for year, c in zip(range(1, 11), cons)
    ])
    
    # План заходів кольоровий
    plan_table = html.Table([html.Tr([html.Th("Рік"), html.Th("Заходи")])] + [
        html.Tr([
            html.Td(year),
            html.Td([html.Span(f"{p['name']} ({p['effect']*100:.1f}%)",
                               style={'color':'white', 'backgroundColor':p['color'],
                                      'padding':'3px 6px', 'margin':'2px','display':'inline-block',
                                      'border-radius':'5px'}) for p in p_list])
        ])
        for year, p_list in zip(range(1, 11), plan)
    ])
    
    return fig, table, plan_table
if __name__ == '__main__':
    app.run(port=8050, debug=True)