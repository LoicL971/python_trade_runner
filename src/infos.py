import datetime
import logging
import pickle as pkl
from src.constants import *
from src.utils import Exchange,Symbol,Interval
import pandas as pd
from src.trade import Trade
from src.chart import Chart
from src.visuals import show_trade,plot_balances
import numpy as np
import os


formatter = logging.Formatter('%(message)s')
def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


class ResultAnalyser(object):
    def __init__(self, exchange:Exchange, symbol:Symbol, interval:Interval, running_trades, archieved_trades):
        self.dts = []
        self.historical_balances = np.array([])
        self.still_running_trades:list[Trade] = running_trades
        self.archieved_trades:list[Trade] = archieved_trades
        self.exchange, self.symbol, self.interval = exchange, symbol, interval
        self.analysed = False
        self.df_trades:pd.DataFrame = None
        self.wr = None
        self.R = None
        self.dd = None
        self.scc = None
        self.stp = None
        self.ccl = None
        self.perf = None


    def put_data(self, current_dt:datetime.datetime, balance):
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
                current_R.append(abs((t.target-t.entry_price)/(t.entry_price-t.market_stop)))
                current_fees_entry.append(t.fees_entry*t.entry_price/dl)
                current_fees_exit.append(t.fees_exit*t.exit_price/dl)
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

    def result_dict(self):
        res = {}
        historical_balances = self.get_historical_balances()
        res["historical_balances"] = {self.dts[i].isoformat(): historical_balances[i] for i in range(len(historical_balances))}
        res["final_gain"] = (historical_balances[-1]-historical_balances[0])/historical_balances[0]
        res["winrate"] = self.get_winrate()
        res["mean_R"] = self.get_r()
        res["max_drawdown"] = self.get_max_drawdown()
        res["succes_count"] = self.get_nb_success()
        res["stopped_count"] = self.get_nb_stopped()
        res["mean_trade_perf"] = self.get_perf()
        return res

    def plot_balances(self):
        self.analyse()
        plot_balances(self.dts, self.historical_balances)
    
    def show_archieved_trade(self, t, width=1, show=True):
        st = t.points[0]
        end = t.dt_closed
        window_sizeh = (end - st)*width
        st = st - window_sizeh
        end = end + window_sizeh
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

    def save_trades(self, dir_path, n=None):
        showed = 1
        if self.archieved_trades:
            print(dir_path)
            os.makedirs(dir_path, exist_ok=True)
        for t in self.archieved_trades:
            if t.closed_state != POSCANCELED:
                with open(dir_path + f"trade{showed}.pkl", "wb") as f:
                    pkl.dump(t, f)
                showed += 1
            if n != None and showed >= n:
                break
        with open(dir_path + f"trade_count.pkl", "wb") as f:
                    pkl.dump(showed-1, f)
            

        
    def fill_ended_trade_logger(self, logger):
        for t in self.archieved_trades:
            if t.closed_state == SUCCESS or t.closed_state == STOPPED:
                msg = t.ended_str()+"\n"
                logger.info(msg)


def show_saved_trade(t, exchange, symbol, interval, width=1, show=True):
    st = t.points[0]
    end = t.dt_closed
    window_sizeh = (end - st)*width
    st = st - window_sizeh
    end = end + window_sizeh
    d = Chart(exchange, symbol, interval, st, end)
    return show_trade(d, t, show)

def html_from_saved_trade(path_to_saved_trades, path_to_html, trade_no, exchange, symbol, interval):
    if os.path.exists(path_to_saved_trades) and os.path.isfile(path_to_saved_trades + f"trade{trade_no}.pkl"):
        with open(path_to_saved_trades + f"trade{trade_no}.pkl", "rb") as f:
            t = pkl.load(f)
        fig = show_saved_trade(t, exchange, symbol, interval, show=False)
        fig.update_layout(title=f"Trade number {trade_no}")
        os.makedirs("/".join(path_to_html.split("/")[:-1]), exist_ok=True)
        fig.write_html(path_to_html)
    else:
        raise FileNotFoundError("Directory or trade file does not exist.")




