from datetime import datetime
import logging
import pickle as pkl
import numpy as np
import os
import pandas as pd

from .chart import Chart
from .constants import *
from .trade import Trade
from .utils import Exchange,Symbol,Interval
from .visuals import show_trade,plot_balances


formatter = logging.Formatter('%(message)s')
def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


class PerformanceManager(object):
    """
    Utilitary class used to builds performance metrics about a setup when performing a backtest
    """
    def __init__(self, exchange:Exchange, symbol:Symbol, interval:Interval, running_trades: list[Trade], archieved_trades: list[Trade]):
        self.dts: list[datetime] = []
        #TODO: use datetime64 from np
        self.historical_balances = np.array([])
        self.still_running_trades:list[Trade] = running_trades
        self.archieved_trades:list[Trade] = archieved_trades
        self.exchange, self.symbol, self.interval = exchange, symbol, interval
        self.analysed: bool = False
        self.df_trades:pd.DataFrame = None
        self.wr: float = None
        self.R: float = None
        self.dd: float = None
        self.scc: int = None
        self.stp: int = None
        self.ccl: int = None
        self.perf: float = None


    def put_data(self, current_dt:datetime, balance):
        self.dts.append(current_dt)
        self.historical_balances = np.append(self.historical_balances, balance)
        if self.analysed:
            self.analysed = False

    def get_historical_balances(self):
        return self.historical_balances
    def get_winrate(self):
        self.analyse()
        return self.wr
    def get_r(self):
        self.analyse()
        return self.R
    def get_max_drawdown(self):
        self.analyse()
        return self.dd
    def get_nb_success(self):
        self.analyse()
        return self.scc
    def get_nb_stopped(self):
        self.analyse()
        return self.stp
    def get_nb_canceled(self):
        self.analyse()
        return self.ccl
    def get_perf(self):
        self.analyse()
        return self.perf


    def df_from_ended_trades(self):
        current_gain = []
        current_R = []
        current_closed_state = []
        current_fees_entry = []
        current_fees_exit = []
        current_gain_coeff = []
        data = {"gain":current_gain, "gain_coeff":current_gain_coeff, "R":current_R, "fees_entry":current_fees_entry, "fees_exit":current_fees_exit, "closed_state":current_closed_state}
        for t in self.archieved_trades:
            current_closed_state.append(t.closed_state)
            dl = abs(t.entry - t.market_stop)
            current_gain.append(t.gain)
            current_gain_coeff.append(t.gain/(t.qty*abs(t.entry-t.market_stop)))
            if t.closed_state == SUCCESS or t.closed_state == STOPPED:
                current_R.append(abs((t.target-t.entry_prices)/(t.entry_prices-t.market_stop)))
                current_fees_entry.append(t.fees_entry*t.entry_prices/dl)
                current_fees_exit.append(t.fees_exit*t.exit_prices/dl)
            else:
                current_R.append(None)
                current_fees_entry.append(None)
                current_fees_exit.append(None)
        self.df_trades = pd.DataFrame(data)
        self.R = self.df_trades["R"].mean()
        self.perf = self.df_trades["gain_coeff"].mean()
        return self.df_trades


    def count_trades(self):
        df = self.df_trades
        self.scc = len(df.loc[df["closed_state"] == SUCCESS])
        self.stp = len(df.loc[df["closed_state"] == STOPPED])
        self.ccl = len(df.loc[df["closed_state"] == POSCANCELED])
        return self.scc, self.stp, self.ccl
    

    def winrate(self, conditions = []):
        """
        condition = [ (column, operator, value), ... ]
        """
        df = self.df_trades
        conditions_success = [("gain", ">", "0")] + conditions
        querry_succes = " & ".join([ col + " " + op + " " + val for col,op,val in conditions_success])
        conditions_stopped = [("gain", "<", "0")] + conditions
        querry_stopped = " & ".join([ col + " " + op + " " + val for col,op,val in conditions_stopped])
        
        success_nb = len(df.query(querry_succes))
        stopped_nb = len(df.query(querry_stopped))
        self.wr = success_nb/(success_nb + stopped_nb)
        return self.wr

    def max_drawdown(self):
        maxs = np.maximum.accumulate(self.historical_balances)
        self.dd = np.max(np.maximum.accumulate(maxs-self.historical_balances)/maxs)
        return self.dd

    def analyse(self):
        if not(self.analysed):
            self.df_from_ended_trades()
            self.winrate()
            self.max_drawdown()
            self.count_trades()
            self.analysed = True

    def plot_balances(self):
        self.analyse()
        plot_balances(self.dts, self.historical_balances)
    
    def show_archieved_trade(self, t, width=1, show=True):
        st = t.points[0]
        end = t.dt_closed
        window_t_delta = (end - st)*width
        st = st - window_t_delta
        end = end + window_t_delta
        d = Chart(self.exchange, self.symbol, self.interval, st, end)
        return show_trade(d, t, show)

    def show_some_archieved_trades(self, n=None, indexes=[]):
        if n != None:
            showed = 0
            for t in self.archieved_trades:
                if t.closed_state != POSCANCELED:
                    self.show_archieved_trade(t)
                    showed += 1
                if showed >= n:
                    break
        if indexes:
            non_canceled_num = 0
            for t in self.archieved_trades:
                if t.closed_state != POSCANCELED:
                    if non_canceled_num in indexes:
                        self.show_archieved_trade(t)
                    non_canceled_num += 1            
        
    def fill_ended_trade_logger(self, logger):
        for t in self.archieved_trades:
            if t.closed_state == SUCCESS or t.closed_state == STOPPED:
                msg = t.ended_trade_to_str()+"\n"
                logger.info(msg)
