from src.chart import *
from typing import Callable, Concatenate, Any

# Un AddPoint permet avec apply_pattern renvoie la points_list actualisee avec tous les points ajoutes à l'index donne selon la fonction donnee
# Un AddPoint permet avec apply_pattern de garder que les points de la points_list qui respecte la condition de f selon les parametres f_parameters

type Points = list[datetime.datetime]

# Ongoing
type Visuals = Any

type FilterFunctionReturnType = tuple[bool, Visuals]
type FilterFunctionType[**P] = Callable[
    Concatenate[Chart, list[datetime.datetime], P], 
    FilterFunctionReturnType
]

type AddFunctionReturnType = tuple[list[datetime.datetime], Visuals]
type AddFunctionType[**P] = Callable[
    Concatenate[Chart, list[datetime.datetime], P], 
    AddFunctionReturnType
]

class Pattern():
    def __init__():
        pass

    def apply_pattern(self, d:Chart, points_list: list[Points]):
        pass

class AddPoint[**P](Pattern):
    def __init__(self, index: int, addf: AddFunctionType[P], *f_parameters: P.args, **kwf_parameters: P.kwargs):
        self.index = index
        self.addf = addf
        self.f_parameters = f_parameters
        self.kwf_parameters = kwf_parameters
    
    def apply_pattern(self, d:Chart, points_list: list[Points], points_visuals: Visuals):
        """
        Returns points_list completed with points to be added according to the pattern
        and visuals required to display the pattern
        """
        res_points_list = []
        res_points_visuals = []
        for i in range(len(points_list)):
            points = points_list[i]
            visuals = points_visuals[i]
            new_points,visual = self.addf(d, points, *self.f_parameters, **self.kwf_parameters)
            for new_point in new_points:
                res_points_list.append(points[:self.index] + [new_point] + points[self.index:])
                res_points_visuals.append(visuals+visual)
        return res_points_list,res_points_visuals


class FilterPoint[**P](Pattern):
    def __init__(self, filter_f: FilterFunctionType[P], *f_parameters: P.args, **kwf_parameters: P.kwargs):
        self.filter_f = filter_f
        self.f_parameters = f_parameters
        self.kwf_parameters = kwf_parameters
    
    def apply_pattern(self, d:Chart, points_list: list[Points], points_visuals: Visuals):
        """
        Returns points_list filtered with points matching the pattern
        and visuals required to display the pattern
        """
        res_points_list = []
        res_points_visuals = []
        for i in range(len(points_list)):
            points = points_list[i]
            visuals = points_visuals[i]
            checked,visual = self.filter_f(d, points, *self.f_parameters, **self.kwf_parameters)
            if checked:
                res_points_list.append(points)
                res_points_visuals.append(visuals+visual)
        return res_points_list,res_points_visuals


def check_highs(d:Chart, points, point_below, point_above) -> FilterFunctionReturnType:
    return d.get_cours(points[point_below])[1] < d.get_cours(points[point_above])[1] , []

def check_lows(d:Chart, points, point_below, point_above) -> FilterFunctionReturnType:
    return d.get_cours(points[point_below])[2] < d.get_cours(points[point_above])[2] , []

def check_high_low(d:Chart, points, point_high_below, point_low_above) -> FilterFunctionReturnType:
    return d.get_cours(points[point_high_below])[1] < d.get_cours(points[point_low_above])[2] , []

def check_low_high(d:Chart, points, point_low_below, point_high_above) -> FilterFunctionReturnType:
    return d.get_cours(points[point_low_below])[2] < d.get_cours(points[point_high_above])[1] , []

def check_fibo(d:Chart, points, point_below, point_above, point_to_check, x_below, x_above, side=1, candle_cross_over_fib=True) -> FilterFunctionReturnType:
    """
    side=1 if above
    side=-1 if below
    """
    limit = (x_below*d.get_cours(points[point_below])[2] + x_above*d.get_cours(points[point_above])[1])#/(x_below+x_above)
    if side == 1:
        if candle_cross_over_fib:
            cours_index = 1
        else:
            cours_index = 2
        return d.get_cours(points[point_to_check])[cours_index] > limit , [("fib", limit)]
    else:
        if candle_cross_over_fib:
            cours_index = 2
        else:
            cours_index = 1
        return d.get_cours(points[point_to_check])[cours_index] < limit , [("fib", limit)]

def check_uptrend(d:Chart, points, point_to_check, end=True) -> FilterFunctionReturnType:
    """
    end = True if point_to_check is ending an uptrend, False if begining
    """
    if end:
        return len(d.get_trend_to(side=1, end_point=points[point_to_check], length=0)) > 0 , []
    else:
        return len(d.get_trend_from(side=1, start_point=points[point_to_check], length=0)) > 0 , []

def check_downtrend(d:Chart, points, point_to_check, end=True) -> FilterFunctionReturnType:
    """
    end = True if point_to_check is ending an downtrend, False if begining
    """
    if end:
        return len(d.get_trend_to(side=-1, end_point=points[point_to_check], length=0)) > 0 , []
    else:
        return len(d.get_trend_from(side=-1, start_point=points[point_to_check], length=0)) > 0 , []

def add_last_datetime(d:Chart, points:list[datetime.datetime]) -> AddFunctionReturnType:
    return [d.final_datetime] , []

def add_above(d:Chart, points:list[datetime.datetime], point:int, before:bool=True) -> AddFunctionReturnType:
    res_point_list:list[datetime.datetime] = []
    if before:
        dt = d.first_datetime
        while dt < points[point] and dt < d.final_datetime:
            if d.get_cours(dt)[1] > d.get_cours(points[point])[1]:
                res_point_list.append(dt)
            dt+=d.dh
    else:
        dt = points[point] + d.dh
        while dt < d.final_datetime:
            if d.get_cours(dt)[1] > d.get_cours(points[point])[1]:
                res_point_list.append(dt)
            dt+=d.dh
    return res_point_list , []

def add_distance() -> AddFunctionReturnType:
    pass

def add_uptrend(d:Chart, points:list[datetime.datetime], point:int, end:bool=True, length:int=0) -> AddFunctionReturnType:
    """
    end = True if point is ending an uptrend, False if begining
    """
    if end:
        return d.get_trend_to(side=1, end_point=points[point], length=length) , []
    else:
        return d.get_trend_from(side=1, start_point=points[point], length=length) , []

def add_downtrend(d:Chart, points:list[datetime.datetime], point:int, end:bool=True, length:int=0) -> AddFunctionReturnType:
    """
    end = True if point is ending an downtrend, False if begining
    """
    if end:
        return d.get_trend_to(side=-1, end_point=points[point], length=length) , []
    else:
        return d.get_trend_from(side=-1, start_point=points[point], length=length) , []