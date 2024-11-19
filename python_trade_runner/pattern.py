from typing import Callable, Concatenate, Any
from datetime import datetime
from abc import ABC, abstractmethod

type Points = list[datetime]

from .chart import Chart

# TODO
type Visuals = Any

type FilterFunctionReturnType = tuple[bool, Visuals]
type FilterFunctionType[**P] = Callable[
    Concatenate[Chart, list[datetime], P], 
    FilterFunctionReturnType
]

type AddFunctionReturnType = tuple[list[datetime], Visuals]
type AddFunctionType[**P] = Callable[
    Concatenate[Chart, list[datetime], P], 
    AddFunctionReturnType
]

class Pattern(ABC):
    """
    Patterns are used to create a setup.

    By defining an apply_pattern, points can be added or removed from a list of presumed setup points to create a setup.
    """
    @abstractmethod
    def apply_pattern(self, d:Chart, points_list: list[Points]):
        pass

class AddPoint[**P](Pattern):
    def __init__(self, index: int, addf: AddFunctionType[P], *f_parameters: P.args, **kwf_parameters: P.kwargs):
        """
        AddPoint patterns are used to add a point at a given index in the setup point list according to addf conditions.
        """
        self.index = index
        self.addf = addf
        self.f_parameters = f_parameters
        self.kwf_parameters = kwf_parameters
    
    def apply_pattern(self, d:Chart, points_list: list[Points], points_visuals: Visuals):
        """
        Returns points_list completed with points to be added according to the pattern and the index position
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
        """
        FilterPoint patterns are used to remove points from the setup point list according to filter_f conditions.
        """
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


def check_highs(d:Chart, points: Points, point_below, point_above) -> FilterFunctionReturnType:
    return d.get_prices(points[point_below])[1] < d.get_prices(points[point_above])[1] , []

def check_lows(d:Chart, points: Points, point_below, point_above) -> FilterFunctionReturnType:
    return d.get_prices(points[point_below])[2] < d.get_prices(points[point_above])[2] , []

def check_high_low(d:Chart, points: Points, point_high_below, point_low_above) -> FilterFunctionReturnType:
    return d.get_prices(points[point_high_below])[1] < d.get_prices(points[point_low_above])[2] , []

def check_low_high(d:Chart, points: Points, point_low_below, point_high_above) -> FilterFunctionReturnType:
    return d.get_prices(points[point_low_below])[2] < d.get_prices(points[point_high_above])[1] , []

def check_fibo(d:Chart, points: Points, point_below, point_above, point_to_check, x_below, x_above, side=1, candle_cross_over_fib=True) -> FilterFunctionReturnType:
    """
    side=1 if above
    side=-1 if below
    """
    limit = (x_below*d.get_prices(points[point_below])[2] + x_above*d.get_prices(points[point_above])[1])#/(x_below+x_above)
    if side == 1:
        if candle_cross_over_fib:
            price_index = 1
        else:
            price_index = 2
        return d.get_prices(points[point_to_check])[price_index] > limit , [("fib", limit)]
    else:
        if candle_cross_over_fib:
            price_index = 2
        else:
            price_index = 1
        return d.get_prices(points[point_to_check])[price_index] < limit , [("fib", limit)]

def check_uptrend(d:Chart, points: Points, point_to_check, end=True) -> FilterFunctionReturnType:
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

def add_last_datetime(d:Chart, points:list[datetime]) -> AddFunctionReturnType:
    return [d.last_datetime] , []

def add_above(d:Chart, points: Points, point:int, before:bool=True) -> AddFunctionReturnType:
    res_point_list:list[datetime] = []
    if before:
        dt = d.first_datetime
        while dt < points[point] and dt < d.last_datetime:
            if d.get_prices(dt)[1] > d.get_prices(points[point])[1]:
                res_point_list.append(dt)
            dt+=d.delta_t
    else:
        dt = points[point] + d.delta_t
        while dt < d.last_datetime:
            if d.get_prices(dt)[1] > d.get_prices(points[point])[1]:
                res_point_list.append(dt)
            dt+=d.delta_t
    return res_point_list , []

def add_distance() -> AddFunctionReturnType:
    pass

def add_uptrend(d:Chart, points: Points, point:int, end:bool=True, length:int=0) -> AddFunctionReturnType:
    """
    end = True if point is ending an uptrend, False if begining
    """
    if end:
        return d.get_trend_to(side=1, end_point=points[point], length=length) , []
    else:
        return d.get_trend_from(side=1, start_point=points[point], length=length) , []

def add_downtrend(d:Chart, points: Points, pt_index:int, end:bool=True, length:int=0) -> AddFunctionReturnType:
    """
    end = True if point is ending an downtrend, False if begining
    """
    if end:
        return d.get_trend_to(side=-1, end_point=points[pt_index], length=length) , []
    else:
        return d.get_trend_from(side=-1, start_point=points[pt_index], length=length) , []