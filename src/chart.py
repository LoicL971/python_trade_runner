import datetime
from pandas import read_csv
import math as m
import numpy as np

from src.utils import Interval,Symbol,Exchange,Candlestick,get_file
from time import time

# Cree le dict des cours ::: create_data apres qui englobe volume et cours et funding rate et ....
vect_cds = np.vectorize(Candlestick)
vect_dts = np.vectorize(lambda ts:datetime.datetime.fromisoformat(ts))
def create_cours(exchange:Exchange, symbol:Symbol, interval:Interval, first_datetime, final_datetime) -> dict:
    cours: dict[datetime.datetime, Candlestick] = {}
    f = get_file(exchange, symbol, interval)

    df = read_csv(f)
    first_dt = datetime.datetime.fromisoformat(df.iloc[0,0])
    start_index = int((first_datetime - first_dt).total_seconds()//interval.value.total_seconds())
    end_index = start_index + int((final_datetime - first_datetime).total_seconds()//interval.value.total_seconds())

    if datetime.datetime.fromisoformat(df.iloc[start_index,0]) != first_datetime:
        msg = "Data " + f + " probably corrupted between " + str(first_dt) + " and " + str(first_datetime)
        raise KeyError(msg)
    if end_index > len(df.index):
        msg = "FinalDateTime out of bounds : " + str(final_datetime) + " last datetime in data : " + str(df.iloc[-1,0])
        raise ValueError(msg)
    if datetime.datetime.fromisoformat(df.iloc[end_index, 0]) != final_datetime:
        msg = "Data " + f + " probably corrupted between " + str(first_datetime) + " and " + str(final_datetime)
        raise KeyError(msg)
    
    df = df.loc[start_index:end_index]
    dts = vect_dts(df["timestamp"].values)
    cds = vect_cds(df["open"].values, df["high"].values, df["low"].values, df["close"].values)
    cours = dict(zip(dts, cds))
    return cours, dts[-1]


# Cree le dict des volumes
# def create_volume():
#     pass

# Cree une liste de min et max
def create_optimums(data) -> list:
    ma = []
    mi = []
    dt_current = data.first_datetime
    dt_next = dt_current+data.dh
    c1 = data.get_cours(dt_current)
    c2 = data.get_cours(dt_next)
    if c1[1] > c2[1]:
        ma.append(dt_current)
    if c1[2] < c2[2]:
        mi.append(dt_current)
    
    #All inner periods
    dt_current = dt_next
    dt_next += data.dh
    c3 = data.get_cours(dt_next)
    if c1[1] <= c2[1] and c2[1] > c3[1]:
        ma.append(dt_current)
    if c1[2] >= c2[2] and c2[2] < c3[2]:
        mi.append(dt_current)
    while dt_next < data.final_datetime:
        dt_current = dt_next
        dt_next += data.dh
        c1 = c2
        c2 = c3
        c3 = data.get_cours(dt_next)
        if c1[1] <= c2[1] and c2[1] > c3[1]:
            ma.append(dt_current)
        if c1[2] >= c2[2] and c2[2] < c3[2]:
            mi.append(dt_current)

    # Finaldatetime
    dt_current = dt_next
    c1 = c2
    c2 = c3
    if c1[1] <= c2[1]:
        ma.append(data.final_datetime)
    if c1[2] >= c2[2]:
        mi.append(data.final_datetime)
    return mi, ma

def update_trends_from_end_points(start_to_ends, end_to_starts, new_end_points, start_point, left_opt=False):
    if new_end_points:
        start_to_ends[start_point] = new_end_points.copy()
        if left_opt:
            for end_point in new_end_points:
                end_to_starts[end_point] = [start_point] + end_to_starts[end_point]
        else:
            for end_point in new_end_points:
                end_to_starts[end_point].append(start_point)

def update_trends_from_start_points(start_to_ends, end_to_starts, new_start_points, end_point, new_left_opt_to_ignore=None):
    if new_start_points:
        end_to_starts[end_point] = new_start_points.copy()
        for start_point in new_start_points:
            if start_point != new_left_opt_to_ignore:
                start_to_ends[start_point].append(end_point)

# renvoie l'ensemble des end_points d'une uptrend partant du minimum i
def find_uptrends_from_min(data, maxs, mins, i):
    end_points = []
    t = mins[i]
    m1 = data.get_cours(t)[2]
    if i < len(mins)-1:
        i2 = i+1
        m2 = data.get_cours(mins[i2])[2]
        while i2 < len(mins) and m1 <= m2:# and data.get_cours(mins[i2]).high < data.get_cours(t).high:
            i2 +=1
            ####### PAS DU TOUT OPTI :(
            if(i2 < len(mins)):
                m2 = data.get_cours(mins[i2])[2]
        if i2 == len(mins):
            tmax = data.final_datetime
        else:
            tmax = mins[i2]
    else:
        tmax = data.final_datetime
    #Recherche dans l'intervalle t, tmax
    cmax = -m.inf
    for t2 in maxs:
        if t2 <= tmax:
            if t2 > t:
                if data.get_cours(t2).low <= data.get_cours(t).low:
                    break
                c = data.get_cours(t2)[1] 
                if c > cmax:
                    cmax = c
                    end_points.append(t2)
        else:
            break
    return end_points

def find_uptrends_from_max(data, maxs, mins, i):
    start_points = []
    t = maxs[i]
    m1 = data.get_cours(t)[1]
    if i > 0:
        i2 = i-1
        m2 = data.get_cours(maxs[i2])[1]
        while i2 >= 0 and m1 > m2:
            i2 -=1
            if(i2 >= 0):
                m2 = data.get_cours(maxs[i2])[1]
        if i2 == -1:
            tmin = data.first_datetime
        else:
            tmin = maxs[i2]
    else:
        tmin = data.first_datetime
    #Recherche dans l'intervalle t, tmin
    cmin = m.inf
    for i2 in range(len(mins)-1, -1, -1):
        t2 = mins[i2]
        # if data.get_cours(t2).high >= data.get_cours(t).high:
        #   break
        # + il faut faire en sorte d'etre tjs au dessus de tmin strict = changement plus haut pour pouvoir cgt l'inégalité.
        # + cmin devrait être max[i] car on peut pas avoir un min > top de up trend = changement ver ingélité stricte mais il faut gérer le fait que ok d'avoir plusieur début de trend egaux.
        if t2 >= tmin:
            if t2 < t:
                if data.get_cours(t2).high >= data.get_cours(t).high:
                    break
                c = data.get_cours(t2)[2]
                if c <= cmin:
                    cmin = c
                    start_points.append(t2)
        else:
            break
    start_points.reverse()
    return start_points

def create_uptrends(data,maxs, mins) -> tuple:
    end_to_starts = {}
    start_to_ends = {}
    for dt in maxs:
        end_to_starts[dt] = []
    for dt in mins:
        start_to_ends[dt] = []
    #Minimums
    i = 0
    # Parallelizable
    while i < len(mins):
        end_points = find_uptrends_from_min(data, maxs, mins, i)
        t = mins[i]
        update_trends_from_end_points(start_to_ends, end_to_starts, end_points, t)
        i+=1
    return end_to_starts,start_to_ends

def find_downtrends_from_max(data, maxs, mins, i):
    end_points = []
    t = maxs[i]
    m1 = data.get_cours(t)[1]
    if i < len(maxs) - 1:
        i2 = i+1
        m2 = data.get_cours(maxs[i2])[1]
        while i2 < len(maxs) and m1 >= m2:# and data.get_cours(maxs[i2]).low < data.get_cours(t).low:
            i2 +=1
            if(i2 < len(maxs)):
                m2 = data.get_cours(maxs[i2])[1]
        if i2 == len(maxs):
            tmax = data.final_datetime
        else:
            tmax = maxs[i2]
    else:
        tmax = data.final_datetime
    #Recherche dans l'intervalle t, tmax
    cmin = m.inf
    for t2 in mins:
        if t2 <= tmax:
            if t2 > t:
                if data.get_cours(t2).high >= data.get_cours(t).high:
                    break
                c = data.get_cours(t2)[2]
                if c < cmin:
                    cmin = c
                    end_points.append(t2)
        else:
            break
    return end_points

###############   Verifier si les trends sont effectivements les meme que en utilisant find_downtrends_from_min   ###############
def find_downtrends_from_min(data, maxs, mins, i):
    start_points = []
    t = mins[i]
    m1 = data.get_cours(t)[2]
    if i > 0:
        i2 = i-1
        m2 = data.get_cours(mins[i2])[2]
        while i2 >= 0 and m1 < m2:# and data.get_cours(mins[i2]).high < data.get_cours(t).high:
            i2 -=1
            ####### PAS DU TOUT OPTI :(
            if(i2 >= 0):
                m2 = data.get_cours(mins[i2])[2]
        if i2 == -1:
            tmin = data.first_datetime
        else:
            tmin = mins[i2]
    else:
        tmin = data.first_datetime
    #Recherche dans l'intervalle t, tmin
    cmax = -m.inf
    for i2 in range(len(maxs)-1, -1, -1):
        t2 = maxs[i2]
        if t2 >= tmin:
            if t2 < t:
                if data.get_cours(t2).low <= data.get_cours(t).low:
                    break
                c = data.get_cours(t2)[1] 
                if c >= cmax:
                    cmax = c
                    start_points.append(t2)
        else:
            break
    start_points.reverse()
    return start_points

def create_downtrends(data,maxs,mins) -> tuple:
    end_to_starts = {}
    start_to_ends = {}
    for dt in mins:
        end_to_starts[dt] = []
    for dt in maxs:
        start_to_ends[dt] = []
    #Maximums
    i = 0
    # Parallelisable
    while i < len(maxs):
        end_points = find_downtrends_from_max(data, maxs, mins, i)
        t = maxs[i]
        update_trends_from_end_points(start_to_ends, end_to_starts, end_points, t)
        i+=1
    return end_to_starts,start_to_ends

def create_emas(cours, first_datetime, final_datetime, emas) -> dict:
    pass

class Chart(object):
    def __init__(self, exchange:Exchange, symbol:Symbol, interval:Interval, start, end, need_trends=False, emas = []):
        self.dh = interval.value
        self.exchange = exchange
        self.symbol = symbol
        self.interval = interval
        self.first_datetime = interval.create_first_datetime(start)
        self.final_datetime = interval.round_time(end)
        self.need_trends = need_trends
        self.need_emas = emas != []
        self.cours, self.final_datetime = create_cours(exchange, symbol, interval, self.first_datetime, self.final_datetime)
        if self.need_trends:
            self.mins, self.maxs = create_optimums(self)
            self.uptrends_end_to_starts,self.uptrends_start_to_ends = create_uptrends(self, self.maxs, self.mins)
            self.downtrends_end_to_starts,self.downtrends_start_to_ends = create_downtrends(self, self.maxs, self.mins)
        if self.need_emas:
            self.emas = create_emas(self, emas)

    def get_cours(self, dt):
        return self.cours[dt]
    
    # def get_volume():
    #     pass

    def get_exchange(self):
        return self.exchange
    
    def get_symbol(self):
        return self.symbol
    
    def get_interval(self):
        return self.interval
    
    def remove_left_min_from_trends(self, mi):
        end_points = self.uptrends_start_to_ends[mi]
        del self.uptrends_start_to_ends[mi]
        for ma in end_points:
            self.uptrends_end_to_starts[ma] = self.uptrends_end_to_starts[ma][1:]
        del self.downtrends_end_to_starts[mi]
    
    def remove_left_max_from_trends(self, ma):
        end_points = self.downtrends_start_to_ends[ma]
        del self.downtrends_start_to_ends[ma]
        for mi in end_points:
            self.downtrends_end_to_starts[mi] = self.downtrends_end_to_starts[mi][1:]
        del self.uptrends_end_to_starts[ma]
    
    def remove_right_min_from_trends(self, mi):
        start_points = self.downtrends_end_to_starts[mi]
        del self.downtrends_end_to_starts[mi]
        for ma in start_points:
            self.downtrends_start_to_ends[ma] = self.downtrends_start_to_ends[ma][:-1]
        del self.uptrends_start_to_ends[mi]
    
    def remove_right_max_from_trends(self, ma):
        start_points = self.uptrends_end_to_starts[ma]
        del self.uptrends_end_to_starts[ma]
        for mi in start_points:
            self.uptrends_start_to_ends[mi] = self.uptrends_start_to_ends[mi][:-1]
        del self.downtrends_start_to_ends[ma]

    def update_left_opt(self):
        c1 = self.get_cours(self.first_datetime)
        c2 = self.get_cours(self.first_datetime + self.dh)
        #min
        dt = self.first_datetime-self.dh
        new_left_min = False
        if self.mins[0] == dt:
            self.remove_left_min_from_trends(dt)
            if c1[2] < c2[2]:
                self.mins[0] = self.first_datetime
                new_left_min = True
            else:
                self.mins = self.mins[1:]
        elif c1[2] < c2[2] and self.mins[0] != self.first_datetime:
            self.mins = [self.first_datetime] + self.mins
            new_left_min = True
        #max
        new_left_max = False
        if self.maxs[0] == dt:
            self.remove_left_max_from_trends(dt)
            if c1[1] > c2[1]:
                new_left_max = True
                self.maxs[0] = self.first_datetime
            else:
                self.maxs = self.maxs[1:]
        elif c1[1] > c2[1] and self.maxs[0] != self.first_datetime:
            self.maxs = [self.first_datetime] + self.maxs
            new_left_max = True
        return new_left_min,new_left_max

    def update_right_opt(self):
        c1 = self.get_cours(self.final_datetime - self.dh)
        c2 = self.get_cours(self.final_datetime)
        #min
        if self.mins[-1] == self.final_datetime-self.dh:
            if c1[2] >= c2[2]:
                self.remove_right_min_from_trends(self.final_datetime-self.dh)
                self.mins[-1] = self.final_datetime
        elif c1[2] >= c2[2]:
            self.mins += [self.final_datetime]
        new_right_min = c1[2] >= c2[2]
        #max
        if self.maxs[-1] == self.final_datetime-self.dh:
            if c1[1] <= c2[1]:
                self.remove_right_max_from_trends(self.final_datetime-self.dh)
                self.maxs[-1] = self.final_datetime
        elif c1[1] <= c2[1]:
            self.maxs += [self.final_datetime]
        new_right_max = c1[1] <= c2[1]
        return new_right_min,new_right_max

    def update_left_trends(self, new_left_min, new_left_max):        
        if new_left_min:
            end_points = find_uptrends_from_min(self, self.maxs, self.mins, 0)
            update_trends_from_end_points(self.uptrends_start_to_ends, self.uptrends_end_to_starts, end_points, self.first_datetime, left_opt=True)
        if new_left_max:
            end_points = find_downtrends_from_max(self, self.maxs, self.mins, 0)
            update_trends_from_end_points(self.downtrends_start_to_ends, self.downtrends_end_to_starts, end_points, self.first_datetime, left_opt=True)

    def update_right_trends(self, new_left_min, new_left_max, new_right_min, new_right_max):
        if new_right_min:
            start_points = find_downtrends_from_min(self, self.maxs, self.mins, len(self.mins)-1)
            if new_left_max and start_points and self.first_datetime == start_points[0]:
                update_trends_from_start_points(self.downtrends_start_to_ends, self.downtrends_end_to_starts, start_points, self.final_datetime, new_left_opt_to_ignore=self.first_datetime)
            else:
                update_trends_from_start_points(self.downtrends_start_to_ends, self.downtrends_end_to_starts, start_points, self.final_datetime)
        if new_right_max:
            start_points = find_uptrends_from_max(self, self.maxs, self.mins, len(self.maxs)-1)
            if new_left_min and start_points and self.first_datetime == start_points[0]:
                update_trends_from_start_points(self.uptrends_start_to_ends, self.uptrends_end_to_starts, start_points, self.final_datetime, new_left_opt_to_ignore=self.first_datetime)
            else:
                update_trends_from_start_points(self.uptrends_start_to_ends, self.uptrends_end_to_starts, start_points, self.final_datetime)

    def update_emas():
        pass
    
    def add_new_points_to_trends(self, new_left_min, new_left_max, new_right_min, new_right_max):
        if new_left_min:
            self.downtrends_end_to_starts[self.first_datetime] = []
            self.uptrends_start_to_ends[self.first_datetime] = []
        if new_left_max:
            self.downtrends_start_to_ends[self.first_datetime] = []
            self.uptrends_end_to_starts[self.first_datetime] = []
        if new_right_min:
            self.downtrends_end_to_starts[self.final_datetime] = []
            self.uptrends_start_to_ends[self.final_datetime] = []
        if new_right_max:
            self.downtrends_start_to_ends[self.final_datetime] = []
            self.uptrends_end_to_starts[self.final_datetime] = []
        self.update_left_trends(new_left_min, new_left_max)
        self.update_right_trends(new_left_min, new_left_max, new_right_min, new_right_max)

        
    def add_next_data(self, dt, cds:Candlestick):
        if dt != self.final_datetime + self.dh:
            msg = "Not adjacent new timestamp, got timestamp : " + str(dt) + " while expecting : " + str(self.final_datetime + self.dh)
            raise ValueError(msg)
        self.cours.pop(self.first_datetime)
        self.cours[dt] = cds
        self.first_datetime += self.dh
        self.final_datetime += self.dh
        if self.need_trends:
            new_left_min,new_left_max = self.update_left_opt()
            new_right_min,new_right_max = self.update_right_opt()
            self.add_new_points_to_trends(new_left_min, new_left_max, new_right_min, new_right_max)
        if self.need_emas:
            self.update_emas()

# Renvoie l'ensemble des points qui commencent une tendance dans le sens side qui s'acheve en dt de longueur length en timestamp ts
    def get_trend_to(self, side:int, end_point:datetime.datetime, length:float=0) -> list[datetime.datetime]:
        """
        side > 0 for uptrend ; 
        side <= 0 for downtrend
        """
        res_start_points = []
        if side > 0:
            if end_point in self.uptrends_end_to_starts:
                for start_point in self.uptrends_end_to_starts[end_point]:
                    if end_point - start_point > length*self.dh:
                        res_start_points.append(start_point)
        else:
            if end_point in self.downtrends_end_to_starts:
                for start_point in self.downtrends_end_to_starts[end_point]:
                    if end_point - start_point > length*self.dh:
                        res_start_points.append(start_point)
        return res_start_points

# Renvoie l'ensemble des points qui terminent une tendance dans le sens side qui commence en dt de longueur length en timestamp ts
    def get_trend_from(self, side:int, start_point:datetime.datetime, length:float=0) -> list[datetime.datetime]:
        """
        side > 0 for uptrend ; 
        side <= 0 for downtrend
        """
        res_end_points = []
        if side > 0:
            if start_point in self.uptrends_start_to_ends:
                for end_point in self.uptrends_start_to_ends[start_point]:
                    if end_point - start_point > length*self.dh:
                        res_end_points.append(end_point)
        else:
            if start_point in self.downtrends_start_to_ends:
                for end_point in self.downtrends_start_to_ends[start_point]:
                    if end_point - start_point > length*self.dh:
                        res_end_points.append(end_point)
        return res_end_points

# Renvoie true s'il y a une trend dans le sens de side qui va de dt_a à dt_b dans le timestamp ts. Si length != None, la longueur de la trend doit etre >= length
    def find_trend(self, side:int, dt_a:datetime.datetime, dt_b:datetime.datetime, length:float) -> bool:
        return (dt_b-dt_a >= length*self.dh) and ((side > 0 and dt_a in self.mins and dt_b in self.uptrends_start_to_ends[dt_a]) or (side < 0 and dt_a in self.maxs and dt_b in self.downtrends_start_to_ends[dt_a]))
