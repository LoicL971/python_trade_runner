from datetime import datetime, timedelta
from pandas import read_csv
import math as m
import numpy as np

from .utils import Interval,Symbol,Exchange,Candlestick,get_file
from .pattern import Points

vect_cds = np.vectorize(Candlestick)
vect_dts = np.vectorize(lambda ts:datetime.fromisoformat(ts))

type Trend = dict[datetime, list[datetime]]

# TODO: include volumes, funding rate, open interests...
def create_prices(exchange:Exchange, symbol:Symbol, interval:Interval, first_datetime: datetime, last_datetime: datetime, data_dir_path: str | None = None) -> tuple[dict[datetime, Candlestick], datetime]:
    prices: dict[datetime, Candlestick] = {}
    f = get_file(exchange, symbol, interval, data_dir_path)

    df = read_csv(f)
    first_dt = datetime.fromisoformat(df.iloc[0,0])
    start_index = int((first_datetime - first_dt).total_seconds()//interval.value.total_seconds())
    end_index = start_index + int((last_datetime - first_datetime).total_seconds()//interval.value.total_seconds())

    if datetime.fromisoformat(df.iloc[start_index,0]) != first_datetime:
        msg = "Data " + f + " probably corrupted between " + str(first_dt) + " and " + str(first_datetime)
        raise KeyError(msg)
    if end_index > len(df.index):
        msg = "FinalDateTime out of bounds : " + str(last_datetime) + " last datetime in data : " + str(df.iloc[-1,0])
        raise ValueError(msg)
    if datetime.fromisoformat(df.iloc[end_index, 0]) != last_datetime:
        msg = "Data " + f + " probably corrupted between " + str(first_datetime) + " and " + str(last_datetime)
        raise KeyError(msg)
    
    df = df.loc[start_index:end_index]
    dts: list[datetime] = vect_dts(df["timestamp"].values)
    cds = vect_cds(df["open"].values, df["high"].values, df["low"].values, df["close"].values)
    prices = dict(zip(dts, cds))
    return prices, dts[-1]

def update_trends_from_end_points(start_to_ends: Trend, end_to_starts: Trend, new_end_points: Points, start_point: datetime, left_opt: bool = False) -> None:
    if new_end_points:
        start_to_ends[start_point] = new_end_points.copy()
        if left_opt:
            for end_point in new_end_points:
                end_to_starts[end_point] = [start_point] + end_to_starts[end_point]
        else:
            for end_point in new_end_points:
                end_to_starts[end_point].append(start_point)

def update_trends_from_start_points(start_to_ends: Trend, end_to_starts: Trend, new_start_points: Points, end_point: datetime, new_left_opt_to_ignore: datetime = None) -> None:
    if new_start_points:
        end_to_starts[end_point] = new_start_points.copy()
        for start_point in new_start_points:
            if start_point != new_left_opt_to_ignore:
                start_to_ends[start_point].append(end_point)

# TODO
def create_emas(prices, first_datetime, last_datetime, emas) -> dict:
    pass

class Chart(object):
    def __init__(self, exchange:Exchange, symbol:Symbol, interval:Interval, start, end, need_trends=False, emas = [], data_dir_path: str | None = None):
        self.delta_t: timedelta = interval.value
        self.exchange = exchange
        self.symbol = symbol
        self.interval = interval
        self.first_datetime = interval.create_first_datetime(start)
        self.last_datetime = interval.round_time(end)
        self.need_trends = need_trends
        self.need_emas = emas != []
        self.prices, self.last_datetime = create_prices(exchange, symbol, interval, self.first_datetime, self.last_datetime, data_dir_path)
        if self.need_trends:
            self.mins, self.maxs = self.create_optimums()
            self.uptrends_end_to_starts,self.uptrends_start_to_ends = self.create_uptrends()
            self.downtrends_end_to_starts,self.downtrends_start_to_ends = self.create_downtrends()
        if self.need_emas:
            self.emas = create_emas(self, emas)

    def create_optimums(self) -> list[datetime]:
        """
        Compute the list optimums in Chart data.

        An optimum is a minimum or a maximum for example: 
        price[t-1] < price[t] and
        price[t+1] < price[t]
        """
        ma = []
        mi = []
        dt_current = self.first_datetime
        dt_next = dt_current+self.delta_t
        p1 = self.get_prices(dt_current)
        p2 = self.get_prices(dt_next)
        if p1[1] > p2[1]:
            ma.append(dt_current)
        if p1[2] < p2[2]:
            mi.append(dt_current)
        
        #All inner periods
        dt_current = dt_next
        dt_next += self.delta_t
        p3 = self.get_prices(dt_next)
        if p1[1] <= p2[1] and p2[1] > p3[1]:
            ma.append(dt_current)
        if p1[2] >= p2[2] and p2[2] < p3[2]:
            mi.append(dt_current)
        while dt_next < self.last_datetime:
            dt_current = dt_next
            dt_next += self.delta_t
            p1 = p2
            p2 = p3
            p3 = self.get_prices(dt_next)
            if p1[1] <= p2[1] and p2[1] > p3[1]:
                ma.append(dt_current)
            if p1[2] >= p2[2] and p2[2] < p3[2]:
                mi.append(dt_current)

        # Last datetime
        dt_current = dt_next
        p1 = p2
        p2 = p3
        if p1[1] <= p2[1]:
            ma.append(self.last_datetime)
        if p1[2] >= p2[2]:
            mi.append(self.last_datetime)
        return mi, ma


    def find_uptrends_from_min(self, i: int) -> list[datetime]:
        """
        Find updtrends starting from index i with a chart initialized with optimums
        """
        end_points: list[datetime] = []
        t = self.mins[i]
        m1 = self.get_prices(t)[2]
        if i < len(self.mins)-1:
            i2 = i+1
            m2 = self.get_prices(self.mins[i2])[2]
            while i2 < len(self.mins) and m1 <= m2:
                i2 +=1
                # TODO: can be optimized
                if(i2 < len(self.mins)):
                    m2 = self.get_prices(self.mins[i2])[2]
            if i2 == len(self.mins):
                tmax = self.last_datetime
            else:
                tmax = self.mins[i2]
        else:
            tmax = self.last_datetime
        # Search between t and tmax
        cmax = -m.inf
        for t2 in self.maxs:
            if t2 <= tmax:
                if t2 > t:
                    if self.get_prices(t2).low <= self.get_prices(t).low:
                        break
                    c = self.get_prices(t2)[1] 
                    if c > cmax:
                        cmax = c
                        end_points.append(t2)
            else:
                break
        return end_points

    def find_uptrends_from_max(self, i: int) -> list[datetime]:
        """
        Find updtrends ending at index i with a chart initialized with optimums
        """
        start_points: list[datetime] = []
        t = self.maxs[i]
        m1 = self.get_prices(t)[1]
        if i > 0:
            i2 = i-1
            m2 = self.get_prices(self.maxs[i2])[1]
            while i2 >= 0 and m1 > m2:
                i2 -=1
                if(i2 >= 0):
                    m2 = self.get_prices(self.maxs[i2])[1]
            if i2 == -1:
                tmin = self.first_datetime
            else:
                tmin = self.maxs[i2]
        else:
            tmin = self.first_datetime
        # Search between t and tmin
        cmin = m.inf
        for i2 in range(len(self.mins)-1, -1, -1):
            t2 = self.mins[i2]
            if t2 >= tmin:
                if t2 < t:
                    if self.get_prices(t2).high >= self.get_prices(t).high:
                        break
                    c = self.get_prices(t2)[2]
                    if c <= cmin:
                        cmin = c
                        start_points.append(t2)
            else:
                break
        start_points.reverse()
        return start_points

    def create_uptrends(self) -> tuple[Trend, Trend]:
        end_to_starts = {}
        start_to_ends = {}
        for dt in self.maxs:
            end_to_starts[dt] = []
        for dt in self.mins:
            start_to_ends[dt] = []
        #Minimums
        i = 0
        # Parallelizable
        while i < len(self.mins):
            end_points = self.find_uptrends_from_min(i)
            t = self.mins[i]
            update_trends_from_end_points(start_to_ends, end_to_starts, end_points, t)
            i+=1
        return end_to_starts,start_to_ends

    def find_downtrends_from_max(self, i: int) -> list[datetime]:
        """
        Find downdtrends starting at index i with a chart initialized with optimums
        """
        end_points: list[datetime] = []
        t = self.maxs[i]
        m1 = self.get_prices(t)[1]
        if i < len(self.maxs) - 1:
            i2 = i+1
            m2 = self.get_prices(self.maxs[i2])[1]
            while i2 < len(self.maxs) and m1 >= m2:
                i2 +=1
                if(i2 < len(self.maxs)):
                    m2 = self.get_prices(self.maxs[i2])[1]
            if i2 == len(self.maxs):
                tmax = self.last_datetime
            else:
                tmax = self.maxs[i2]
        else:
            tmax = self.last_datetime
        # Search between t and tmax
        cmin = m.inf
        for t2 in self.mins:
            if t2 <= tmax:
                if t2 > t:
                    if self.get_prices(t2).high >= self.get_prices(t).high:
                        break
                    c = self.get_prices(t2)[2]
                    if c < cmin:
                        cmin = c
                        end_points.append(t2)
            else:
                break
        return end_points

    def find_downtrends_from_min(self, i: int) -> list[datetime]:
        start_points: list[datetime] = []
        t = self.mins[i]
        m1 = self.get_prices(t)[2]
        if i > 0:
            i2 = i-1
            m2 = self.get_prices(self.mins[i2])[2]
            while i2 >= 0 and m1 < m2:
                i2 -=1
                # TODO: can be optimized
                if(i2 >= 0):
                    m2 = self.get_prices(self.mins[i2])[2]
            if i2 == -1:
                tmin = self.first_datetime
            else:
                tmin = self.mins[i2]
        else:
            tmin = self.first_datetime
        #Recherche dans l'intervalle t, tmin
        cmax = -m.inf
        for i2 in range(len(self.maxs)-1, -1, -1):
            t2 = self.maxs[i2]
            if t2 >= tmin:
                if t2 < t:
                    if self.get_prices(t2).low <= self.get_prices(t).low:
                        break
                    c = self.get_prices(t2)[1] 
                    if c >= cmax:
                        cmax = c
                        start_points.append(t2)
            else:
                break
        start_points.reverse()
        return start_points

    def create_downtrends(self) -> tuple[Trend, Trend]:
        end_to_starts = {}
        start_to_ends = {}
        for dt in self.mins:
            end_to_starts[dt] = []
        for dt in self.maxs:
            start_to_ends[dt] = []
        #Maximums
        i = 0
        # Parallelizable
        while i < len(self.maxs):
            end_points = self.find_downtrends_from_max(i)
            t = self.maxs[i]
            update_trends_from_end_points(start_to_ends, end_to_starts, end_points, t)
            i+=1
        return end_to_starts,start_to_ends

    def get_prices(self, dt: datetime) -> Candlestick:
        return self.prices[dt]
    
    def get_exchange(self) -> Exchange:
        return self.exchange
    
    def get_symbol(self) -> Symbol:
        return self.symbol
    
    def get_interval(self) -> Interval:
        return self.interval
    
    def remove_left_min_from_trends(self, mi: datetime) -> None:
        end_points = self.uptrends_start_to_ends[mi]
        del self.uptrends_start_to_ends[mi]
        for ma in end_points:
            self.uptrends_end_to_starts[ma] = self.uptrends_end_to_starts[ma][1:]
        del self.downtrends_end_to_starts[mi]
    
    def remove_left_max_from_trends(self, ma: datetime) -> None:
        end_points = self.downtrends_start_to_ends[ma]
        del self.downtrends_start_to_ends[ma]
        for mi in end_points:
            self.downtrends_end_to_starts[mi] = self.downtrends_end_to_starts[mi][1:]
        del self.uptrends_end_to_starts[ma]
    
    def remove_right_min_from_trends(self, mi: datetime) -> None:
        start_points = self.downtrends_end_to_starts[mi]
        del self.downtrends_end_to_starts[mi]
        for ma in start_points:
            self.downtrends_start_to_ends[ma] = self.downtrends_start_to_ends[ma][:-1]
        del self.uptrends_start_to_ends[mi]
    
    def remove_right_max_from_trends(self, ma: datetime) -> None:
        start_points = self.uptrends_end_to_starts[ma]
        del self.uptrends_end_to_starts[ma]
        for mi in start_points:
            self.uptrends_start_to_ends[mi] = self.uptrends_start_to_ends[mi][:-1]
        del self.downtrends_start_to_ends[ma]

    def update_left_opt(self) -> tuple[bool, bool]:
        p1 = self.get_prices(self.first_datetime)
        p2 = self.get_prices(self.first_datetime + self.delta_t)
        #min
        dt = self.first_datetime-self.delta_t
        new_left_min = False
        if self.mins[0] == dt:
            self.remove_left_min_from_trends(dt)
            if p1[2] < p2[2]:
                self.mins[0] = self.first_datetime
                new_left_min = True
            else:
                self.mins = self.mins[1:]
        elif p1[2] < p2[2] and self.mins[0] != self.first_datetime:
            self.mins = [self.first_datetime] + self.mins
            new_left_min = True
        #max
        new_left_max = False
        if self.maxs[0] == dt:
            self.remove_left_max_from_trends(dt)
            if p1[1] > p2[1]:
                new_left_max = True
                self.maxs[0] = self.first_datetime
            else:
                self.maxs = self.maxs[1:]
        elif p1[1] > p2[1] and self.maxs[0] != self.first_datetime:
            self.maxs = [self.first_datetime] + self.maxs
            new_left_max = True
        return new_left_min,new_left_max

    def update_right_opt(self) -> tuple[bool, bool]:
        p1 = self.get_prices(self.last_datetime - self.delta_t)
        p2 = self.get_prices(self.last_datetime)
        #min
        if self.mins[-1] == self.last_datetime-self.delta_t:
            if p1[2] >= p2[2]:
                self.remove_right_min_from_trends(self.last_datetime-self.delta_t)
                self.mins[-1] = self.last_datetime
        elif p1[2] >= p2[2]:
            self.mins += [self.last_datetime]
        new_right_min = p1[2] >= p2[2]
        #max
        if self.maxs[-1] == self.last_datetime-self.delta_t:
            if p1[1] <= p2[1]:
                self.remove_right_max_from_trends(self.last_datetime-self.delta_t)
                self.maxs[-1] = self.last_datetime
        elif p1[1] <= p2[1]:
            self.maxs += [self.last_datetime]
        new_right_max = p1[1] <= p2[1]
        return new_right_min,new_right_max

    def update_left_trends(self, new_left_min: bool, new_left_max: bool) -> None:        
        if new_left_min:
            end_points = self.find_uptrends_from_min(0)
            update_trends_from_end_points(self.uptrends_start_to_ends, self.uptrends_end_to_starts, end_points, self.first_datetime, left_opt=True)
        if new_left_max:
            end_points = self.find_downtrends_from_max(0)
            update_trends_from_end_points(self.downtrends_start_to_ends, self.downtrends_end_to_starts, end_points, self.first_datetime, left_opt=True)

    def update_right_trends(self, new_left_min: bool, new_left_max: bool, new_right_min: bool, new_right_max: bool) -> None:
        if new_right_min:
            start_points = self.find_downtrends_from_min(len(self.mins)-1)
            if new_left_max and start_points and self.first_datetime == start_points[0]:
                update_trends_from_start_points(self.downtrends_start_to_ends, self.downtrends_end_to_starts, start_points, self.last_datetime, new_left_opt_to_ignore=self.first_datetime)
            else:
                update_trends_from_start_points(self.downtrends_start_to_ends, self.downtrends_end_to_starts, start_points, self.last_datetime)
        if new_right_max:
            start_points = self.find_uptrends_from_max(len(self.maxs)-1)
            if new_left_min and start_points and self.first_datetime == start_points[0]:
                update_trends_from_start_points(self.uptrends_start_to_ends, self.uptrends_end_to_starts, start_points, self.last_datetime, new_left_opt_to_ignore=self.first_datetime)
            else:
                update_trends_from_start_points(self.uptrends_start_to_ends, self.uptrends_end_to_starts, start_points, self.last_datetime)

    # TODO
    def update_emas():
        pass
    
    def add_new_points_to_trends(self, new_left_min: bool, new_left_max: bool, new_right_min: bool, new_right_max: bool) -> None:
        if new_left_min:
            self.downtrends_end_to_starts[self.first_datetime] = []
            self.uptrends_start_to_ends[self.first_datetime] = []
        if new_left_max:
            self.downtrends_start_to_ends[self.first_datetime] = []
            self.uptrends_end_to_starts[self.first_datetime] = []
        if new_right_min:
            self.downtrends_end_to_starts[self.last_datetime] = []
            self.uptrends_start_to_ends[self.last_datetime] = []
        if new_right_max:
            self.downtrends_start_to_ends[self.last_datetime] = []
            self.uptrends_end_to_starts[self.last_datetime] = []
        self.update_left_trends(new_left_min, new_left_max)
        self.update_right_trends(new_left_min, new_left_max, new_right_min, new_right_max)

        
    def add_next_data(self, dt: datetime, cds: Candlestick) -> None:
        if dt != self.last_datetime + self.delta_t:
            msg = "Not adjacent new timestamp, got timestamp : " + str(dt) + " while expecting : " + str(self.last_datetime + self.delta_t)
            raise ValueError(msg)
        self.prices.pop(self.first_datetime)
        self.prices[dt] = cds
        self.first_datetime += self.delta_t
        self.last_datetime += self.delta_t
        if self.need_trends:
            new_left_min,new_left_max = self.update_left_opt()
            new_right_min,new_right_max = self.update_right_opt()
            self.add_new_points_to_trends(new_left_min, new_left_max, new_right_min, new_right_max)
        if self.need_emas:
            self.update_emas()

    # TODO: side = LONG | SHORT instead of int
    def get_trend_to(self, side: int, end_point: datetime, length: float=0) -> list[datetime]:
        """
        Return a list of the starting points of trends that end on "end_points" and which
        length is greater than "length".

        side > 0 for uptrend ; 
        side <= 0 for downtrend
        """
        res_start_points = []
        if side > 0:
            if end_point in self.uptrends_end_to_starts:
                for start_point in self.uptrends_end_to_starts[end_point]:
                    if end_point - start_point > length*self.delta_t:
                        res_start_points.append(start_point)
        else:
            if end_point in self.downtrends_end_to_starts:
                for start_point in self.downtrends_end_to_starts[end_point]:
                    if end_point - start_point > length*self.delta_t:
                        res_start_points.append(start_point)
        return res_start_points

    def get_trend_from(self, side: int, start_point: datetime, length: float=0) -> list[datetime]:
        """
        Return a list of the ending points of trends that start on "start_points" and which
        length is greater than "length".

        side > 0 for uptrend ; 
        side <= 0 for downtrend
        """
        res_end_points = []
        if side > 0:
            if start_point in self.uptrends_start_to_ends:
                for end_point in self.uptrends_start_to_ends[start_point]:
                    if end_point - start_point > length*self.delta_t:
                        res_end_points.append(end_point)
        else:
            if start_point in self.downtrends_start_to_ends:
                for end_point in self.downtrends_start_to_ends[start_point]:
                    if end_point - start_point > length*self.delta_t:
                        res_end_points.append(end_point)
        return res_end_points

    def find_trend(self, side: int, dt_a: datetime, dt_b: datetime, length: float | None) -> bool:
        """
        Returns true if a trend starts from "dt_a" and ends in "dt_b" with a length >= "length
        Returns false otherwise

        side > 0 for uptrend ; 
        side <= 0 for downtrend
        """
        return (dt_b-dt_a >= length*self.delta_t) and ((side > 0 and dt_a in self.mins and dt_b in self.uptrends_start_to_ends[dt_a]) or (side < 0 and dt_a in self.maxs and dt_b in self.downtrends_start_to_ends[dt_a]))
