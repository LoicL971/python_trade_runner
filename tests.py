import datetime
from src import chart
from src import utils

exch = utils.Exchange.BYBIT
symb = utils.Symbol.BTCUSDT
interv = utils.Interval.M5

start = datetime.datetime(2022, 3, 3, 12, 0, tzinfo=datetime.timezone.utc)
end = datetime.datetime(2022, 3, 3, 17, 0, tzinfo=datetime.timezone.utc)
data = chart.Chart(exch, symb, interv, start, end, True)

d = datetime.datetime(2022, 3, 3, 14, 10, tzinfo=datetime.timezone.utc)

print(data.up_trends_start_to_ends.keys())
print(len(data.up_trends_start_to_ends[d]))
for t in data.up_trends_start_to_ends[d]:
    print(t)