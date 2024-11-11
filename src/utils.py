import datetime
from enum import Enum
from src.constants import LONG, SHORT

class Interval(Enum):
    M1:datetime.timedelta = datetime.timedelta(seconds=60)
    M5:datetime.timedelta = datetime.timedelta(seconds=300)
    M15:datetime.timedelta = datetime.timedelta(seconds=900)
    M30:datetime.timedelta = datetime.timedelta(seconds=1800)
    H1:datetime.timedelta = datetime.timedelta(seconds=3600)
    H4:datetime.timedelta = datetime.timedelta(seconds=14400)
    H12:datetime.timedelta = datetime.timedelta(seconds=43200)
    D1:datetime.timedelta = datetime.timedelta(seconds=86400)

    def __lt__(self, other):
        return self.value < other.value
    
    def __gt__(self, other):
        return self.value > other.value
    
    def __ge__(self, other):
        return self.value >= other.value

    def __le__(self, other):
        return self.value <= other.value
    
    def round_time(self, dt:datetime):
        if self < Interval.H1:
            return datetime.datetime(year = dt.year, month = dt.month, day = dt.day, hour = dt.hour, minute= int(self.value.total_seconds()/60*(dt.minute//(self.value.total_seconds()/60))), tzinfo=datetime.timezone.utc)
        elif self < Interval.D1:
            return datetime.datetime(year = dt.year, month = dt.month, day = dt.day, hour = int(self.value.total_seconds()/3600*(dt.hour//(self.value.total_seconds()/3600))), tzinfo=datetime.timezone.utc)
        else:
            return datetime.datetime(year = dt.year, month = dt.month, day = dt.day, tzinfo=datetime.timezone.utc)

    def create_first_datetime(self, start):
        dt = self.round_time(start)
        if dt < start:
            dt += self.value
        return dt
    
    def to_str(self):
        if self == Interval.M1:
            return "1m"
        elif self == Interval.M5:
            return "5m"
        elif self == Interval.M15:
            return "15m"
        elif self == Interval.M30:
            return "30m"
        elif self == Interval.H1:
            return "1h"
        elif self == Interval.H4:
            return "4h"
        elif self == Interval.H12:
            return "12h"
        elif self == Interval.D1:
            return "1d"
        else:
            raise ValueError("Interval not recognized")
        
    def from_str(s):
        if s == "1m":
            return Interval.M1
        elif s == "5m":
            return Interval.M5
        elif s == "15m":
            return Interval.M15
        elif s == "30m":
            return Interval.M30
        elif s == "1h":
            return Interval.H1
        elif s == "4h":
            return Interval.H4
        elif s == "12h":
            return Interval.H12
        elif s == "1d":
            return Interval.D1
        else:
            raise ValueError("Interval not recognized")

TIMES = {Interval.M1:1, Interval.M5: 5, Interval.M15:15, Interval.M30:30, Interval.H1: 60, Interval.H4:240, Interval.H12:720,Interval.D1:"D"}


class Symbol(Enum):
    BTCUSDT:str = "BTCUSDT"
    ETHUSDT:str = "ETHUSDT"
    SOLUSDT:str = "SOLUSDT"

    def to_str(self):
        if self == Symbol.BTCUSDT:
            return "BTCUSDT"
        elif self == Symbol.ETHUSDT:
            return "ETHSUDT"
        elif self == Symbol.SOLUSDT:
            return "SOLUSDT"
        else:
            raise ValueError("Symbol not recognized")
    
    def from_str(s):
        if s == "BTCUSDT":
            return Symbol.BTCUSDT
        elif s == "ETHUSDT":
            return Symbol.ETHUSDT
        elif s == "SOLUSDT":
            return Symbol.SOLUSDT
        else:
            raise ValueError("Symbol not recognized")
    
class Exchange(Enum):
    BYBIT:str = "bybit"
    BINANCE:str = "binance"
    BITMEX:str = "bitmex"

    def to_str(self):
        if self == Exchange.BYBIT:
            return "bybit"
        elif self == Exchange.BINANCE:
            return "binance"
        elif self == Exchange.BITMEX:
            return "bitmex"
        else:
            raise ValueError("Exchange not recognized")
    
    def from_str(s):
        if s == "bybit":
            return Exchange.BYBIT
        elif s == "binance":
            return Exchange.BINANCE
        elif s == "bitmex":
            return Exchange.BITMEX
        else:
            raise ValueError("Exchange not recognized")

# fees_maker,fees_taker
FEES = {Exchange.BYBIT:(0.0001,0.0006)}

def get_file(exchange:Exchange, symbol:Symbol, interval:Interval):
    return f"data/{exchange.to_str()}/{symbol.to_str()}/{exchange.to_str()}-{symbol.to_str()}-{interval.to_str()}.csv"

class Candlestick():
    def __init__(self, o=None, h=None, l=None, c=None):
        self.open = o
        self.close = c
        self.high = h
        self.low = l
    
    def side_to_value(self, side):
        """
        if side == LONG : return LOW
        if side == SHORT : return HIGH 
        """
        if side == LONG : return self.low
        if side == SHORT : return self.high 

    def __getitem__(self, key):
        if key == 0:
            return self.open
        elif key == 1:
            return self.high
        elif key == 2:
            return self.low
        elif key == 3:
            return self.close
        else:
            msg = "Key given to __setitem__ should be among 0 ; 1 ; 2 ; 3 not : " + str(key)
            raise KeyError(msg)
    
    def __setitem__(self, key, value):
        if type(value) != float and type(value) != int:
            msg = "Value given to __setitem__ should be float or int not : " + str(type(value))
            raise TypeError(msg)
        elif key == 0:
            self.open = value
        elif key == 1:
            self.high = value
        elif key == 2:
            self.low = value
        elif key == 3:
            self.close = value
        else:
            msg = "Key given to __setitem__ should be among 0 ; 1 ; 2 ; 3 not : " + str(key)
            raise KeyError(msg)

    def __str__(self):
        return f"({self.open},{self.high},{self.low},{self.close})"

