from time import time
from datetime import datetime, timezone

from python_trade_runner import *

def test_backtest_result():
    pattern_list = []
    pattern_list.append(AddPoint(0, add_last_datetime))
    pattern_list.append(AddPoint(0, add_uptrend, 0, True))
    pattern_list.append(AddPoint(0, add_downtrend, 0, True))
    pattern_list.append(AddPoint(0, add_uptrend, 0, True))
    pattern_list.append(AddPoint(0, add_downtrend, 0, True))
    pattern_list.append(FilterPoint(check_highs, 2, 0))
    pattern_list.append(FilterPoint(check_highs, 4, 2))
    pattern_list.append(FilterPoint(check_lows, 1, 3))
    trade_builder = TradeBuilder([(2,1,1)], [(1,2,1)], [(1,2,-1),(2,1,2)], market_entry=True, max_trade_duration_params=[0,3,0.5], visual_price_index=[1,2,1,2,1])

    setup = Setup(0, pattern_list, trade_builder)

    start = datetime(2022,6,15,tzinfo=timezone.utc)
    end = datetime(2022,6,21,tzinfo=timezone.utc)
    exchange=Exchange.BINANCE
    symbol=Symbol.BTCUSDT
    interval=Interval.M5

    b = Backtest(setup_list=[setup], risk_for_setup_id={0:0.01}, start_datetime=start, end_datetime=end, window_size=150, initial_balance=1000, 
            exchange=exchange, symbol=symbol, interval=interval, test_fees=False)
    b.initialize_chart()
    b.step_untill_end()
    result = b.get_results()
    assert result.get_winrate() ==  0.5294117647058824
    assert result.get_r() ==  1.0
    assert result.get_max_drawdown() ==  0.17051894344254878
    assert result.get_perf() ==  -0.021641658105929308
    assert result.get_nb_success() ==  27
    assert result.get_nb_stopped() ==  24
    assert result.get_nb_canceled() ==  28
    assert b.balance ==  972.2956319148449


def test_deserialized_backtest_result():
    serialized_pattern_list = "paLdt&0$paUT&0&0&T$paDT&0&0&T$paUT&0&0&T$paDT&0&0&T$pcHgh&2&0$pcHgh&4&2$pcLw&1&3"
    serialized_trade_builder = "2!1!1&$1!2!1&$1!2!-1&2!1!2$T$0&3&0.5$1&2&1&2&1"
    serialized_setup = serialized_pattern_list + "_" + serialized_trade_builder
    setup = deserialize_setup(serialized_setup)

    start = datetime(2022,6,15,tzinfo=timezone.utc)
    end = datetime(2022,6,21,tzinfo=timezone.utc)
    exchange=Exchange.BINANCE
    symbol=Symbol.BTCUSDT
    interval=Interval.M5

    b = Backtest(setup_list=[setup], risk_for_setup_id={0:0.01}, start_datetime=start, end_datetime=end, window_size=150, initial_balance=1000, 
            exchange=exchange, symbol=symbol, interval=interval, test_fees=False)
    b.initialize_chart()
    b.step_untill_end()
    result = b.get_results()
    assert result.get_winrate() ==  0.5294117647058824
    assert result.get_r() ==  1.0
    assert result.get_max_drawdown() ==  0.17051894344254878
    assert result.get_perf() ==  -0.021641658105929308
    assert result.get_nb_success() ==  27
    assert result.get_nb_stopped() ==  24
    assert result.get_nb_canceled() ==  28
    assert b.balance ==  972.2956319148449
