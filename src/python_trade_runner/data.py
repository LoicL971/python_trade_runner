from datetime import datetime

from .chart import Chart
from .utils import Interval,Symbol,Exchange,Candlestick

# TODO: this class will be used for multiple Interval / Symbol setups
class Data(object):
    def __init__(self, charts:list[Chart]):
        self.charts = {}
        for chart in charts:
            if not(chart.get_exchange() in self.charts):
                self.charts[chart.get_exchange()] = {}
            if not(chart.get_symbol() in self.charts[chart.get_exchange()]):
                self.charts[chart.get_exchange()][chart.get_symbol()] = {}
            self.charts[chart.get_exchange()][chart.get_symbol()][chart.get_interval()] = chart
    
    def get_prices(self, exchange:Exchange, symbol:Symbol, interval:Interval, dt) -> Candlestick:
        return self.charts[exchange][symbol][interval].get_prices(dt)
    
    def add_next_data(self, exchange:Exchange, symbol:Symbol, interval:Interval, dt, cds:Candlestick):
        self.charts[exchange][symbol][interval].add_next_data(dt, cds)
    
    def get_trend_to(self, exchange:Exchange, symbol:Symbol, interval:Interval, side:int, end_point:datetime, length:float=0) -> list[datetime]:
        return self.charts[exchange][symbol][interval].get_trend_to(side, end_point, length)
    
    def get_trend_from(self, exchange:Exchange, symbol:Symbol, interval:Interval, side:int, start_point:datetime, length:float=0) -> list[datetime]:
        return self.charts[exchange][symbol][interval].get_trend_from(side, start_point, length)
    
    def find_trend(self, exchange:Exchange, symbol:Symbol, interval:Interval, side:int, dt_a:datetime, dt_b:datetime, length:float) -> bool:
        return self.charts[exchange][symbol][interval].find_trend(side, dt_a, dt_b, length)