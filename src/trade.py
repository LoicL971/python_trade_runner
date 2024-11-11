from src.chart import Chart
from src.constants import FEESMAKER, FEESTAKER, OPTIONALUNDEF,POSITION, CLOSED, RUNNING, STOPPED, SUCCESS, OVERTIMED, POSCANCELED, LONG, SHORT
from src.utils import Candlestick

def auto_size(balance, entry, stop, risk):
    qty = balance*risk/(abs(entry-stop))
    return qty

def gain(side, entry_price, exit_price, qty, fees_entry, fees_exit):
    return qty * (exit_price - entry_price) * side - (fees_entry*qty*entry_price + fees_exit*qty*exit_price)


def get_filled_price(side, cds:Candlestick, order_price, gaps=True):
    """
    Handles gaps or setups that throw late signals
    """
    if not(gaps) or (cds.open-order_price)*side > 0:
        return order_price
    else:
        return cds.open

def calculate_fees(fees, qty, price):
    return fees*qty*price

### Quand j'ajoute market_entry, penser a modifier le filtre des trades dans le back test pour pas que market_entry soit confondu avec entry
### Ajouter prise en compte des GAPS
class Trade:
    #Always one entry and one target, to simulate multiple entries and target, use multiple setups
    def __init__(self, balance, risk, dt_position, entry, target, market_stop, fees, points, market_entry:bool=False, slippage = 0, visuals={}):
        self.state = POSITION
        self.entry = entry
        self.target = target
        self.market_stop = market_stop
        self.market_entry = market_entry
        self.points = points
        self.visuals = visuals
        if self.entry > self.market_stop:
            self.side = LONG
        else:
            self.side = SHORT
        self.qty = auto_size(balance, entry, market_stop, risk)
        self.entry_price = None
        self.dt_position = dt_position
        self.exit_price = None
        self.dt_filled = None
        self.dt_closed = None
        self.gain = None
        self.closed_state = None
        self.fees = fees
        self.fees_entry = None
        self.fees_exit = None
        self.slippage = slippage
        #Optional
        self.duree_position = OPTIONALUNDEF
        self.id_setup = OPTIONALUNDEF
    
    def check_position(self, cds:Candlestick, dt):
        #if long and l < entry or if short and h > entry
        if not(self.market_entry) and 0 < (self.entry-cds.side_to_value(self.side))*self.side:
            self.entry_price = get_filled_price(self.side, cds, self.entry)
            self.state = RUNNING
            self.dt_filled = dt
            self.fees_entry = self.fees[FEESMAKER]
        elif self.market_entry and 0 > (self.entry-cds.side_to_value(-self.side))*self.side:
            self.entry_price = get_filled_price(-self.side, cds, self.entry)
            self.state = RUNNING
            self.dt_filled = dt
            self.fees_entry = self.fees[FEESTAKER]
        elif self.duree_position != OPTIONALUNDEF and dt-self.dt_position>self.duree_position:
            self.state = CLOSED
            self.closed_state = POSCANCELED
            self.dt_closed = dt
            self.gain = 0
    
    def check_running(self, cds:Candlestick, dt):
        #if long and l < market_stop or if short and h > market_stop
        if 0 < (self.market_stop-cds.side_to_value(self.side))*self.side:
            #without this if, trade were stopped during the same datetimes they were filled if it was market entry and cds open was < marketstop
            #actually, we don't know if during the cds price goes only up or if it get back to stop the trade
            #so adding this if is optimistic but ok
            if not(dt == self.dt_filled and self.market_entry and 0 < (self.market_stop-cds.open)*self.side):
                self.exit_price = get_filled_price(self.side, cds, self.market_stop)*(1 - self.side*self.slippage)
                self.state = CLOSED
                self.closed_state = STOPPED
                self.fees_exit = self.fees[FEESTAKER]
                self.dt_closed = dt
                self.gain = gain(self.side, self.entry_price, self.exit_price, self.qty, self.fees_entry, self.fees_exit)
        #if long and h > target or if short and l < target
        elif (cds.side_to_value(-self.side)-self.target)*self.side > 0:
            #same problem as last if, we don't want to trigger tp on limit entry if cds open is higher than tp during same dt it was filled
            if self.market_entry or dt > self.dt_filled:
                self.exit_price = get_filled_price(-self.side, cds, self.target)
                self.state = CLOSED
                self.closed_state = SUCCESS
                self.fees_exit = self.fees[FEESMAKER]
                self.dt_closed = dt
                self.gain = gain(self.side, self.entry_price, self.exit_price, self.qty, self.fees_entry, self.fees_exit)

    def check_trade(self, cds:Candlestick, dt):
        if self.state == POSITION:
            self.check_position(cds,dt)
        if self.state == RUNNING:
            self.check_running(cds,dt)
        if self.state == CLOSED:
            return self.gain

    def ended_str(self):
        if self.side == LONG:
            s = "long"
        else:
            s = "short"
        return f"{str(self.dt_closed)} - Closed {s} with state {self.closed_state} with gain of {self.gain}USD entry at {self.entry_price}$/BTC exit at {self.exit_price}$/BTC, positioned at {self.dt_position}"


class TradeBuilder():
    def __init__(self, coeffs_entry, coeffs_market_stop, coeffs_target,
                market_entry, params_duree_position=None, visual_cours_index=None):
        """
        coeffs as [ (point_index,cours_index,coeff), ...] -> cours[point_index][cours_index]*coeff + ... ; \n
        duree_position as [point_a, point_b, coeff] -> duree_position = (points[point_b] - points[point_a])*coeff \n
        market_entry = True -> stop buy or sell at entry point
        """
        self.coeffs_entry = coeffs_entry
        self.coeffs_market_stop = coeffs_market_stop
        self.coeffs_target = coeffs_target
        self.market_entry = market_entry
        self.params_duree_position = params_duree_position
        self.visual_cours_index = visual_cours_index
        self.fees = 0,0
    
    def set_maker_taker_fees(self, fees_maker=0, fees_taker=0):
        self.fees = fees_maker,fees_taker

    def get_order_price(self, d:Chart, points, coeffs) -> float:
        price = 0
        for i in range(len(coeffs)):
            point_index,cours_index,coeff = coeffs[i]
            price += coeff*d.get_cours(points[point_index])[cours_index]
        return price
    
    def get_trade(self, d:Chart, points, id_setup, dt_position, risk, balance, visuals={}) -> Trade:
        if self.visual_cours_index:
            visuals["cours_index"] = self.visual_cours_index
        entry = self.get_order_price(d, points, self.coeffs_entry)
        market_stop = self.get_order_price(d, points, self.coeffs_market_stop)
        target = self.get_order_price(d, points, self.coeffs_target)
        t = Trade(balance, risk, dt_position, entry, target, market_stop, self.fees, points, self.market_entry, visuals=visuals)
        t.id_setup = id_setup
        if self.params_duree_position != None:
            t.duree_position = (points[self.params_duree_position[1]] - points[self.params_duree_position[0]])*self.params_duree_position[2]
        return t
        





