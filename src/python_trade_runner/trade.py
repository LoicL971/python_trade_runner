from datetime import datetime

from .pattern import Points
from .chart import Chart
from .constants import FEESMAKER, FEESTAKER, OPTIONALUNDEF,POSITION, CLOSED, RUNNING, STOPPED, SUCCESS, OVERTIMED, POSCANCELED, LONG, SHORT
from .utils import Candlestick

def auto_size(balance, entry, stop, risk):
    qty = balance*risk/(abs(entry-stop))
    return qty

def gain(side: int, entry_price: float, exit_price: float, qty: float, fees_entry: float, fees_exit: float) -> float:
    return qty * (exit_price - entry_price) * side - (fees_entry*qty*entry_price + fees_exit*qty*exit_price)


def get_filled_price(side, cds:Candlestick, order_price: float, gaps=True) -> float:
    """
    Handles gaps or setups that throw late signals
    """
    if not(gaps) or (cds.open-order_price)*side > 0:
        return order_price
    else:
        return cds.open

def calculate_fees(fees: float, qty: float, price: float) -> float:
    return fees*qty*price

# TODO: handle gaps
class Trade:
    def __init__(self, balance: float, risk: float, dt_position: datetime, entry: float, target: float, market_stop: float, fees: float, points: Points, market_entry=False, slippage: float = 0, visuals={}):
        self.state = POSITION
        self.entry = entry
        self.target = target
        # TODO: check confusion with entry in backtest filters
        self.market_stop = market_stop
        self.market_entry = market_entry
        self.points = points
        self.visuals = visuals
        if self.entry > self.market_stop:
            self.side = LONG
        else:
            self.side = SHORT
        self.qty = auto_size(balance, entry, market_stop, risk)
        self.entry_prices = None
        self.dt_position = dt_position
        self.exit_prices = None
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
    
    def step_forward_position(self, cds:Candlestick, dt: datetime) -> None:
        #if long and l < entry or if short and h > entry
        if not(self.market_entry) and 0 < (self.entry-cds.side_to_value(self.side))*self.side:
            self.entry_prices = get_filled_price(self.side, cds, self.entry)
            self.state = RUNNING
            self.dt_filled = dt
            self.fees_entry = self.fees[FEESMAKER]
        elif self.market_entry and 0 > (self.entry-cds.side_to_value(-self.side))*self.side:
            self.entry_prices = get_filled_price(-self.side, cds, self.entry)
            self.state = RUNNING
            self.dt_filled = dt
            self.fees_entry = self.fees[FEESTAKER]
        elif self.duree_position != OPTIONALUNDEF and dt-self.dt_position>self.duree_position:
            self.state = CLOSED
            self.closed_state = POSCANCELED
            self.dt_closed = dt
            self.gain = 0
    
    def step_forward_running(self, cds:Candlestick, dt: datetime) -> None:
        #if long and l < market_stop or if short and h > market_stop
        if 0 < (self.market_stop-cds.side_to_value(self.side))*self.side:
            # without this if, trade were stopped during the same datetimes they were filled if it was market entry and cds open was < marketstop
            # actually, we don't know if during the cds prices goes only up or if it get back to stop the trade
            # so adding this if is optimistic but ok
            if not(dt == self.dt_filled and self.market_entry and 0 < (self.market_stop-cds.open)*self.side):
                self.exit_prices = get_filled_price(self.side, cds, self.market_stop)*(1 - self.side*self.slippage)
                self.state = CLOSED
                self.closed_state = STOPPED
                self.fees_exit = self.fees[FEESTAKER]
                self.dt_closed = dt
                self.gain = gain(self.side, self.entry_prices, self.exit_prices, self.qty, self.fees_entry, self.fees_exit)
        #if long and h > target or if short and l < target
        elif (cds.side_to_value(-self.side)-self.target)*self.side > 0:
            #same problem as last if, we don't want to trigger tp on limit entry if cds open is higher than tp during same dt it was filled
            if self.market_entry or dt > self.dt_filled:
                self.exit_prices = get_filled_price(-self.side, cds, self.target)
                self.state = CLOSED
                self.closed_state = SUCCESS
                self.fees_exit = self.fees[FEESMAKER]
                self.dt_closed = dt
                self.gain = gain(self.side, self.entry_prices, self.exit_prices, self.qty, self.fees_entry, self.fees_exit)

    def step_forward(self, cds:Candlestick, dt) -> None | float:
        if self.state == POSITION:
            self.step_forward_position(cds,dt)
        if self.state == RUNNING:
            self.step_forward_running(cds,dt)
        if self.state == CLOSED:
            return self.gain

    def ended_trade_to_str(self):
        if self.side == LONG:
            s = "long"
        else:
            s = "short"
        return f"{str(self.dt_closed)} - Closed {s} with state {self.closed_state} with gain of {self.gain}USD entry at {self.entry_prices}$/BTC exit at {self.exit_prices}$/BTC, positioned at {self.dt_position}"

type Coeff = tuple[int, int, float]
class TradeBuilder():
    """
    Create a Trade from points computed after applying a Setup.

    Trade entries, targets and stop levels are computed with linear combination of points yielded by a setup.
    coeffs are used for the linear combination.
    """
    def __init__(self, coeffs_entry: list[Coeff], coeffs_market_stop: list[Coeff], coeffs_target: list[Coeff],
                market_entry: bool, max_trade_duration_params: Coeff | None = None, visual_price_index=None):
        """
        Create a Trade from points computed after applying a Setup.

        Trade entries, targets and stop levels are computed with linear combination of points yielded by a setup.
        coeffs are used for the linear combination.
        
        coeffs are used as [ (point_index,price_index,coeff), ...] -> price[point_index][price_index]*coeff + ... ; \n
        max_trade_duration as [point_a, point_b, coeff] -> max_trade_duration = (points[point_b] - points[point_a])*coeff \n
        market_entry = True -> stop buy or sell at entry point
        """
        self.coeffs_entry = coeffs_entry
        self.coeffs_market_stop = coeffs_market_stop
        self.coeffs_target = coeffs_target
        self.market_entry = market_entry
        self.max_trade_duration_params = max_trade_duration_params
        self.visual_price_index = visual_price_index
        self.fees = 0.,0.
    
    def set_maker_taker_fees(self, fees_maker=0., fees_taker=0.) -> None:
        self.fees = fees_maker,fees_taker

    def get_order_price(self, d:Chart, points: Points, coeffs: list[Coeff]) -> float:
        price = 0.
        for i in range(len(coeffs)):
            point_index,price_index,coeff = coeffs[i]
            price += coeff*d.get_prices(points[point_index])[price_index]
        return price
    
    def create_trade(self, d:Chart, points: Points, id_setup: str, dt_position: datetime, risk: float, balance: float, visuals={}) -> Trade:
        if self.visual_price_index:
            visuals["price_index"] = self.visual_price_index
        entry = self.get_order_price(d, points, self.coeffs_entry)
        market_stop = self.get_order_price(d, points, self.coeffs_market_stop)
        target = self.get_order_price(d, points, self.coeffs_target)
        t = Trade(balance, risk, dt_position, entry, target, market_stop, self.fees, points, self.market_entry, visuals=visuals)
        t.id_setup = id_setup
        if self.max_trade_duration_params != None:
            t.duree_position = (points[self.max_trade_duration_params[1]] - points[self.max_trade_duration_params[0]])*self.max_trade_duration_params[2]
        return t
        





