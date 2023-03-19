import dash
from dash import dcc
from dash import html
import plotly.graph_objs as go
import requests
from plotly.subplots import make_subplots
from dash.dependencies import Input, Output
import time
import json

# Define the API endpoint
endpoint = "https://opstra.definedge.com/api/openinterest/optionchain/"
cookies = {
    "JSESSIONID": "BCACEC8FD4D8F06C9968F222F88110AB",
    "_gid": "GA1.2.1873885370.1679171256",
    "_gat": "1",
    "_ga": "GA1.2.1729389628.1671716279"
}

# Define the Dash app
app = dash.Dash(__name__)

def calculate_gamma_exposure(chain):
    gamma_exposure = {}
    for data in chain:
        strike_price = data['StrikePrice']
        call_gamma = data['CallGamma']
        call_oi = data['CallOI']
        put_gamma = data['PutGamma']
        put_oi = data['PutOI']
        
        gamma_exposure[strike_price] = (call_gamma*call_oi*100) + (put_gamma*put_oi*-100)
        
    return gamma_exposure

def get_option_chain(symbol, expiry_date):
    url = f'https://opstra.definedge.com/api/openinterest/optionchain/{symbol}&{expiry_date}'
    cookies = {
    "JSESSIONID": "BCACEC8FD4D8F06C9968F222F88110AB",
    "_gid": "GA1.2.1873885370.1679171256",
    "_gat": "1",
    "_ga": "GA1.2.1729389628.1671716279"
}
    response = requests.get(url, cookies=cookies )
    data = json.loads(response.text)['data']
    
    return data

def get_max_gammas(chain):
    max_call_gamma_strike = None
    max_positive_gamma = 0
    max_put_gamma_strike = None
    max_negative_gamma = 0
    
    for data in chain:
        strike_price = data['StrikePrice']
        call_gamma = data['CallGamma'] * data['CallOI'] * 100
        put_gamma = data['PutGamma'] * data['PutOI'] * -100
        gamma_exposure = call_gamma + put_gamma
        
        if gamma_exposure > max_positive_gamma:
            max_positive_gamma = gamma_exposure
            max_call_gamma_strike = strike_price
        
        if gamma_exposure < max_negative_gamma:
            max_negative_gamma = gamma_exposure
            max_put_gamma_strike = strike_price
    
    return max_call_gamma_strike, max_put_gamma_strike

def check_entry(gamma_exposure, spot_price, max_call_gamma_strike, max_put_gamma_strike):
    for strike_price, gamma in gamma_exposure.items():
        if sum(gamma_exposure) > 0:
            if spot_price -25 < strike_price < spot_price +25:
                if strike_price == max_call_gamma_strike:
                    # buy put option
                    return 'BUY PUT'
                elif strike_price == max_put_gamma_strike:
                    # buy call option
                    return 'BUY CALL'
        elif sum(gamma_exposure) < 0:
            if spot_price -25 < strike_price < spot_price +25:
                if strike_price == max_call_gamma_strike:
                    # buy put option
                    return 'BUY CALL'
                elif strike_price == max_put_gamma_strike:
                    # buy call option
                    return 'BUY PUT'        
        """ if spot_price -25 < strike_price < spot_price +25:
            if strike_price == max_call_gamma_strike:
                # buy put option
                return 'BUY PUT'
            elif strike_price == max_put_gamma_strike:
                # buy call option
                return 'BUY CALL' """
    
    return 'NO TRADE'
    

# Define the app layout
app.layout = html.Div([
    html.H1("Gamma Exposure"),
    dcc.Input(id="symbol", type="text", placeholder="Enter the symbol"),
    dcc.Input(id="expiry_date", type="text", placeholder="Expiry date (eg. 23MAR2023)"),
    html.Button(id="submit-button", n_clicks=0, children="Submit"),
    dcc.Interval(id="interval-component", interval=30*1000, n_intervals=0),
    dcc.Graph(id="output")
])

# Define the callback function for the button
@app.callback(
    dash.dependencies.Output("output", "figure"),
    [dash.dependencies.Input("submit-button", "n_clicks")],
    [dash.dependencies.State("symbol", "value"), dash.dependencies.State("expiry_date", "value")],
    [Input('interval-component', 'n_intervals')]
)
def calculate_gamma(n_clicks, symbol, expiry_date,n_intervals):
    if n_clicks > 0:
        # Make the API request
        url = endpoint + symbol + "&" + expiry_date
        response = requests.get(url, cookies=cookies)
        spot_url = f"https://h9cg992bof.execute-api.ap-south-1.amazonaws.com/webapi/symbol/today-spot-data?symbol={symbol}"
        response_spot = requests.get(spot_url)
        dataa = response_spot.json()
        result_data = dataa["resultData"]
        max_pain = result_data.get("max_pain")
        change_value = result_data.get("change_value")
        last_trade_price = result_data.get("last_trade_price")
        spot_price = last_trade_price # replace with actual spot price
        option_chain = get_option_chain(symbol, expiry_date)
        gamma_exposure = calculate_gamma_exposure(option_chain)
        max_call_gamma_strike, max_put_gamma_strike = get_max_gammas(option_chain)
        entry_signal = check_entry(gamma_exposure, spot_price, max_call_gamma_strike, max_put_gamma_strike)
        print(max_call_gamma_strike)
        print(max_put_gamma_strike)
        print(entry_signal)
        # print(sum(gamma_exposure))
        print("Spot price:",last_trade_price, " Max pain:",max_pain, " Change: ",change_value)
        if response.status_code == 200:
            data = response.json()["data"]
            gamma_exposure = {}
            for item in data:
                strike_price = item["StrikePrice"]
                call_gamma = item["CallGamma"]
                call_oi = item["CallOI"]
                put_gamma = item["PutGamma"]
                put_oi = item["PutOI"]
                call_gamma_exposure = call_oi * 100 * call_gamma
                put_gamma_exposure = put_oi * -100 * put_gamma
                gamma_exposure[strike_price] = call_gamma_exposure + put_gamma_exposure
            # Create a bar graph of the gamma exposure for each strike

            fig = make_subplots(rows=1, cols=1)
            # Create a list of colors based on the values of gamma exposure
            colors = ['green' if gamma > 0 else 'red' for gamma in gamma_exposure.values()]

            #fig.add_trace(go.Bar(x=list(gamma_exposure.keys()), y=list(gamma_exposure.values()), name='Gamma Exposure'), row=1, col=1)
            fig.add_trace(go.Bar(x=list(gamma_exposure.keys()), y=list(gamma_exposure.values()), name='Gamma Exposure',
                     marker=dict(color=colors)), row=1, col=1)

            # plot the bar graph of gamma exposure levels
            """ fig.add_trace(go.Scatter(x=[spot_price], y=[0], mode='markers', name='Spot Price'), row=2, col=1)
            fig.add_trace(go.Scatter(x=[max_call_gamma_strike, max_put_gamma_strike], y=[0, 0], mode='markers', name='Buy/Sell'), row=2, col=1) """

            # add vertical line for spot price
            fig.update_layout(
                shapes=[
                    dict(
                        type='line',
                        x0=spot_price,
                        y0=0,
                        x1=spot_price,
                        y1=max(gamma_exposure.values()),
                        line=dict(color='black', width=2)
                    ),
                    dict(
                        type='line',
                        x0=spot_price,
                        y0=0,
                        x1=spot_price,
                        y1=min(gamma_exposure.values()),
                        line=dict(color= 'black', width=2)
                    )
                ], 
                    annotations=[
                        dict(
                            x=spot_price,
                            y=max(gamma_exposure.values()),
                            xref="x",
                            yref="y",
                            text=f"Spot Price: {spot_price}, {time.strftime('%H:%M:%S')}, Buy/Sell: {entry_signal}, Total Exposure: {sum(gamma_exposure)}",
                            showarrow=True,
                            arrowhead=1,
                            ax=0,
                            ay=-40
                        )
                    ]
            )

            fig.update_layout(height=800, title='Option Chain Analysis')

            """ fig.show()

            fig = go.Figure(
                data=[go.Bar(x=list(gamma_exposure.keys()), y=list(gamma_exposure.values()))],
                layout=go.Layout(
                    title=go.layout.Title(text="Gamma Exposure by Strike Price"),
                    xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Strike Price")),
                    yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Gamma Exposure"))
                )
            ) """
            return fig
        else:
            return {}
    else:
        return {}

if __name__ == "__main__":
    app.run_server(debug=True)
