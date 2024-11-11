from src.constants import CLOSED, LONG, SHORT
from src.trade import Trade, gain
from src.setup import *
from src.utils import FEES, Interval, Exchange, Symbol
from src.constants import *
import datetime
from src.infos import ResultAnalyser



# Fonction d'ajout des trades a la trade_list
#Penser a remodifier le jour ou ca gere plus de 1 trade a la fois
def base_add_trade(b, t:Trade):
    duplicate = False
    i = 0
    while i < len(b.trade_list) and not(duplicate):
        t2 = b.trade_list[i]
        if not(t.market_entry) and t.side == t2.side:
            if (t.side==LONG and t.entry >= t2.entry) or (t.side==SHORT and t.entry <= t2.entry):
                duplicate = True
        elif t.market_entry and t.side == t2.side and t.entry == t2.entry:
            duplicate = True
        i+=1
    if not(duplicate):
        b.trade_list.append(t)
        return True
    else:
        return False

# Fonction pour filter les nouveaux trades généré par un setup sur une step
def base_new_trade_filter(b, trade_list:list[Trade]):
    res = []
    for t in trade_list:
        fees_entry = t.fees[FEESTAKER] if t.market_entry else t.fees[FEESMAKER]
        fees_exit = t.fees[FEESMAKER]
        if gain(t.side, t.entry, t.target, t.qty, fees_entry, fees_exit) > 0:
            res.append(t)
    return res

### quand multiple symboles et vart, ce sera pris en compte dans le setup et ce ne sera pas le backtest qui va selectionner les données a donner au setup
### le backtest donnera tout le d et le setup selectionnera les infos utiles

class Backtest(object):
    def __init__(self, setup_list:list[Setup], risk_for_setup_id:dict, start_datetime:datetime.datetime, end_datetime:datetime.datetime, window_size:int, initial_balance:float,
                 exchange:Exchange, symbol:Symbol, interval:Interval, test_fees=False, f_add_trade=base_add_trade, f_new_trade_filter=base_new_trade_filter):
        self.setup_list:list[Setup] = setup_list
        self.risk_for_setup_id:dict = risk_for_setup_id
        self.start_datetime:datetime.datetime = interval.create_first_datetime(start_datetime)
        self.end_datetime:datetime.datetime = interval.round_time(end_datetime)
        self.window_size = window_size
        self.balance = initial_balance
        self.interval = interval
        self.symbol = symbol
        self.exchange = exchange
        self.f_add_trade = f_add_trade
        self.f_new_trade_filter = f_new_trade_filter

        self.test_fees = test_fees
        if not(self.test_fees):
            for setup in self.setup_list:
                setup.trade_builder.set_maker_taker_fees(*FEES[self.exchange])

        self.CHART:Chart = None
        self.current_chart:Chart = None
        self.current_dt:datetime.datetime = None
        self.trade_list:list[Trade] = []
        self.archieved_trades:list[Trade] = []
        self.results_analyser = ResultAnalyser(self.exchange, self.symbol, self.interval, self.trade_list, self.archieved_trades)

### on parcours la liste des setups et on return les symbols qu on a besoin, les intervals, need_trends, need_emas et tous les indicateurs qu on a besoin
# sert à la creation de chart d
    def setups_needs(self):
        pass
    
    def get_results(self):
        return self.results_analyser

# provisoire par la suite utilisera setup_needs
### tester taille window_size obtenue sur current_chart
    def initialize_chart(self):
        self.CHART = Chart(self.exchange, self.symbol, self.interval, self.start_datetime, self.end_datetime, need_trends=False)
        self.current_dt = self.start_datetime + self.interval.value*(self.window_size + 1)
        self.current_chart = Chart(self.exchange, self.symbol, self.interval, self.start_datetime, self.current_dt-self.interval.value, need_trends=True)

    def check_all_trades(self):
        cds = self.current_chart.get_cours(self.current_chart.final_datetime)
        to_remove = []

        for t in self.trade_list:
            t.check_trade(cds,self.current_chart.final_datetime)
            if t.state == CLOSED:
                to_remove.append(t)
                self.archieved_trades.append(t)
                self.balance += t.gain
        for t in to_remove:
            self.trade_list.remove(t)
            # show_trade(self.current_chart, t)

    def put_new_trades(self):
        for setup in self.setup_list:
            nt = setup.get_new_trades(self.current_chart, self.current_dt, self.risk_for_setup_id[setup.id_setup], self.balance)
            nt = self.f_new_trade_filter(self, nt)
            for t in nt:
                self.f_add_trade(self, t)


### calcule infos sur balance + max drawdown + toutes les infos que j ai besoin a chaque tour, necessitera peut etre une nouvelle classe info qui contiendra toutes mes infos ou une datastruct
    def analyse_info(self):
        self.results_analyser.put_data(self.current_dt, self.balance)

    def incr_dt(self):
        if self.current_dt < self.end_datetime:  
            cds = self.CHART.get_cours(self.current_dt)
            self.current_chart.add_next_data(self.current_dt, cds)
            self.current_dt += self.current_chart.dh
        else:
            print("Unable to incr_dt")

    def step(self):
        self.check_all_trades()
        self.put_new_trades()
        self.analyse_info()
        self.incr_dt()

    def step_untill_end(self):
        while self.current_dt < self.end_datetime:
            self.step()
        return self
        


