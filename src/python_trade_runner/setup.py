import re

from .chart import Chart
from .pattern import *
from .trade import TradeBuilder
from .visuals import Visual

id_max = 0

def create_dict_visuals(visuals: list[tuple[datetime, float]]) -> dict[str, list[float]]:
    dict_visuals: dict[str, list[float]] = {}
    for key,val in visuals:
        if key in dict_visuals:
            if not(val in dict_visuals[key]):
                dict_visuals[key].append(val)
        else:
            dict_visuals[key] = [val]
    return dict_visuals

class Setup(object):
    def __init__(self, id_setup:int, pattern_list:list[Pattern], trade_builder:TradeBuilder):
        self.id_setup = id_setup
        self.pattern_list = pattern_list
        self.trade_builder = trade_builder


    def get_new_points(self, d:Chart):
        points_list = [[]]
        points_visuals = [[]]
        for pattern in self.pattern_list:
            points_list,points_visuals = pattern.apply_pattern(d=d, points_list=points_list, points_visuals=points_visuals)
        return points_list,points_visuals
    
    def get_new_trades(self, d:Chart, dt_position: datetime, risk: float, balance: float):
        trades_list = []
        points_list,points_visuals = self.get_new_points(d)
        for i in range(len(points_list)):
            points = points_list[i]
            visuals = points_visuals[i]
            dict_visuals = create_dict_visuals(visuals)
            t = self.trade_builder.create_trade(d, points, self.id_setup, dt_position, risk, balance, dict_visuals)
            trades_list.append(t)
        return trades_list
            
## DESERIALIZATION OF PatternLIST : 
# delimiters between list obj "$",
# delimiters between params "&" 
# naming :  pa+code add function
#           pc+code check function
# types : if -?only digits  -> int
#           -?digits.digits -> float
#           T               -> True 
#           F               -> False
def get_check_func(s:str):
    if s == "pcHgh":
        return check_highs
    elif s == "pcLw":
        return check_lows
    elif s == "pcHL":
        return check_high_low
    elif s == "pcLH":
        return check_low_high
    elif s == "pcFib":
        return check_fibo
    elif s == "pcUT":
        return check_uptrend
    elif s == "pcDT":
        return check_downtrend
    
    else:
        raise ValueError("Unrecognized check function")

def get_add_func(s:str):
    if s == "paLdt":
        return add_last_datetime
    elif s == "paAb":
        return add_above
    elif s == "paDist":
        return add_distance
    elif s == "paUT":
        return add_uptrend
    elif s == "paDT":
        return add_downtrend
    else:
        raise ValueError("Unrecognized add function")


def get_func(s:str):
    if len(s) > 2:
        if s[:2] == "pa":
            return get_add_func(s),True
        elif s[:2] == "pc":
            return get_check_func(s),False
        else:
            raise ValueError("Function type unrecognized")
    else:
        raise ValueError("Invalid function serialization")

def get_index(s:str):
    if re.fullmatch(r"\d+", s):
        return int(s)
    else:
        raise ValueError("Unrecognized index")

def get_parameter(s:str):
    if s == "T":
        return True
    elif s == "F":
        return False
    elif re.fullmatch(r"-?\d+\.\d*", s):
        return float(s)
    elif re.fullmatch(r"-?\d+", s):
        return int(s)
    else:
        raise ValueError("Unrecognized parameter")

def deserialize_pattern_list(serialized_list:str) -> list[Pattern]:
    pattern_list:list[Pattern] = []
    f_list = serialized_list.split('$')
    for s in f_list:
        s_list = s.split('&')
        f,add_function = get_func(s_list[0])
        if add_function:
            f_index = get_index(s_list[1])
            f_parameters = []
            for s2 in s_list[2:]:
                f_parameters.append(get_parameter(s2))
            pattern_list.append(AddPoint(f_index, f, *f_parameters))
        else:
            f_parameters = []
            for s2 in s_list[1:]:
                f_parameters.append(get_parameter(s2))
            pattern_list.append(FilterPoint(f, *f_parameters))
    return pattern_list

   
## DESERIALIZATION OF TRADE BUILDER : 
# delimiters between params $ 
# delimiters between list obj "&",
# delimiters between tuple obj "!",
# 2,[(1,23,3),(1,2)],6 -> 2$1!23!3&1!2&6
# types : if -?only digits  -> int
#           -?digits.digits -> float
#           T               -> True 
#           F               -> False
def create_tuple(serialized_tuple:str):
    """
    deserialize tuple if is a tuple or deserialize parameter if is't tuple
    """
    if '!' in serialized_tuple:
        tuple_elems = serialized_tuple.split("!")
        return tuple(get_parameter(elem) for elem in tuple_elems if elem)
    else:
        return get_parameter(serialized_tuple)

def create_list(serialized_list:str):
    if '&' in serialized_list:
        list_elems = serialized_list.split('&')
        return list(create_tuple(elem) for elem in list_elems if elem)
    else:
        return create_tuple(serialized_list)


def deserialize_trade_builer(serialised_trade_builder:str) -> TradeBuilder:
    args = []
    p_list = serialised_trade_builder.split("$") 
    for parameter in p_list:
        args.append(create_list(parameter))
    return TradeBuilder(*args)

def deserialize_setup(serialized_setup:str) -> Setup:
    serialized_pattern_list,serialized_trade_builder = serialized_setup.split('_')
    pfl = deserialize_pattern_list(serialized_pattern_list)
    tb = deserialize_trade_builer(serialized_trade_builder)
    setup = Setup(0, pfl, tb)
    return setup
