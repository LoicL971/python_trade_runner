import plotly.graph_objects as go

from .chart import Chart
from .trade import Trade

# TODO
type Visual = dict

def get_fig_data(d:Chart):
    X,O,H,L,C = [],[],[],[],[]
    for ts2,prices in d.prices.items():
        X.append(ts2)
        O.append(prices[0])
        H.append(prices[1])
        L.append(prices[2])
        C.append(prices[3])
    fig = go.Figure(data=[go.Candlestick(x=X,open=O,high=H,low=L,close=C)])
    fig.update_layout(xaxis_rangeslider_visible=False)
    return fig

def add_visual_price_index(d:Chart, t:Trade, fig: go.Figure):
    visual_price_index = t.visuals["price_index"]
    for i in range(len(t.points)-1):
        x0 = t.points[i]
        x1 = t.points[i+1]
        y0 = d.get_prices(t.points[i])[visual_price_index[i]]
        y1 = d.get_prices(t.points[i+1])[visual_price_index[i+1]]
        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color="RoyalBlue",width=2))

def add_visual_fib(d:Chart, t:Trade, fig: go.Figure):
    for y_fib in t.visuals["fib"]:
        fig.add_hline(y=y_fib, line_width=1, line_dash="dash", line_color="green")

def add_setup_points(d:Chart, t:Trade, fig: go.Figure):
    if len(t.points) == 1:
        fig.add_vrect(x0=t.points[0],x1=t.points[0],line_width=0.5, fillcolor="black", opacity=0.5)
    if t.visuals:
        if "price_index" in t.visuals:
            add_visual_price_index(d, t, fig)
        if "fib" in t.visuals:
            add_visual_fib(d, t, fig)
    
            

def add_trade_values(d:Chart, t:Trade, fig: go.Figure):
    sens = t.side
    entree = t.entry
    stop = t.market_stop
    target = t.target
    ts1 = t.dt_position
    if t.dt_closed == None and t.duree_position != None:
        ts2 = ts1 + t.duree_position
        fig.add_shape(type="rect", x0=ts1, y0=entree, x1=ts2, y1=target, line=dict(color="RoyalBlue", width=2,), fillcolor="green",opacity=0.5,)
        fig.add_shape(type="rect", x0=ts1, y0=entree, x1=ts2, y1=stop, line=dict(color="RoyalBlue", width=2,), fillcolor="red",opacity=0.5,)
    elif t.dt_closed != None:
        ts2 = t.dt_filled
        ts3 = t.dt_closed
        entry_prices = t.entry_prices
        exit_prices = t.exit_prices
        fig.add_shape(type="rect", x0=ts1, y0=entree, x1=ts2, y1=target, line=dict(color="RoyalBlue", width=2,), fillcolor="green",opacity=0.5,)
        fig.add_shape(type="rect", x0=ts2, y0=entry_prices, x1=ts3, y1=target, line=dict(color="RoyalBlue", width=2,), fillcolor="green",opacity=0.6,)
        fig.add_shape(type="rect", x0=ts1, y0=entree, x1=ts2, y1=stop, line=dict(color="RoyalBlue", width=2,), fillcolor="red",opacity=0.5,)
        fig.add_shape(type="rect", x0=ts2, y0=entry_prices, x1=ts3, y1=stop, line=dict(color="RoyalBlue", width=2,), fillcolor="red",opacity=0.6,)

def show_data(d:Chart):
    fig = get_fig_data(d)
    fig.show()


# Changer la duree pour integrer fin du trade
def show_trade(d:Chart, t:Trade, show:bool=True):
    fig = get_fig_data(d)
    add_setup_points(d, t, fig)
    add_trade_values(d, t, fig)
    if show:
        fig.show()
    return fig


def plot_balances(dts, balances):
    fig = go.Figure(data=go.Scatter(x=dts, y=balances, line=dict(color='firebrick', width=4)), )
    fig.update_layout(title='Historical balances',
                   xaxis_title='Time',
                   yaxis_title='Balance')
    fig.show()
