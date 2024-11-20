# python_trade_runner

A Python helper for backtesting and running trading strategies.

**python_trade_runner** is a Python package designed to assist in backtesting and executing trading strategies. It provides tools to simulate trading strategies on historical data and facilitates their deployment in live trading environments.

---

## Features

- **Backtesting Framework**: Simulate trading strategies against historical market data to evaluate performance and robustness.
- **Live Trading Support** *(coming soon)*: Seamlessly transition from backtesting to live trading.
- **Modular Design**: Easily integrate custom strategies and indicators.

---

## Table of Contents

- [Installation](#installation)
- [Getting Started](#getting-started)
  - [1. Import Your Data](#1-import-your-data)
  - [2. Import Required Modules](#2-import-required-modules)
  - [3. Define Your Strategy](#3-define-your-strategy)
  - [4. Backtest Your Strategy](#4-backtest-your-strategy)
  - [5. Analyze Results](#5-analyze-results)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Installation

To install the package, clone the repository and install the dependencies:

```bash
git clone https://github.com/loicl971/python_trade_runner.git
cd python_trade_runner
pip install -r requirements.txt
```

## Getting started
### 1. Import your data
Your financial data should follow the same format as the files in `test/data`.

- **Data Format**: The dataset should be a CSV file containing candlestick data with the following six columns:
    - `timestamp`, `open`, `high`, `low`, `close` and `volume`
- **Path Structure**: `{PATH_TO_DATA}/{exchange}/{symbol}/{exchange}-{symbol}-{interval}.csv`
You can set your custom data folder by overwriting `PATH_TO_DATA`.

You can create a data folder and reference it by overwriting `PATH_TO_DATA`.

### 2. Import required modules
Import all necessary modules or specific ones as needed:
```python
from python_trade_runner import *  # Or import specific classes/functions
```

### 3. Define your strategy
#### Create a Trading Pattern
Define a list of patterns to design your trading strategy. For example, the following defines a [double bottom pattern](https://www.investopedia.com/terms/d/doublebottom.asp):
```python
pattern_list = []
pattern_list.append(AddPoint(0, add_last_datetime))
pattern_list.append(AddPoint(0, add_uptrend, 0, True))
pattern_list.append(AddPoint(0, add_downtrend, 0, True))
pattern_list.append(AddPoint(0, add_uptrend, 0, True))
pattern_list.append(AddPoint(0, add_downtrend, 0, True))
pattern_list.append(FilterPoint(check_highs, 2, 0))
pattern_list.append(FilterPoint(check_highs, 4, 2))
pattern_list.append(FilterPoint(check_lows, 1, 3))
```

#### Create a Trade Builder
A trade builder calculates the trade position based on your pattern, including entry, stop loss, and profit levels:
```python
trade_builder = TradeBuilder(
    [(2, 1, 1)],
    [(1, 2, 1)],
    [(1, 2, -1), (2, 1, 2)],
    market_entry=True,
    max_trade_duration_params=[0, 3, 0.5],
    visual_price_index=[1, 2, 1, 2, 1]
)
```

#### *Trade Position Calculation*
In this example, the trade position is defined using the following parameters:

- **Entry Level**: The maximum candlestick price at point **C**.
- **Stop Level**: The minimum candlestick price at point **B**.
- **Profit Level**: Calculated using the formula:
  \[
  \text{Profit Level} = 2 \times (\text{candlestick max price from point C}) - (\text{candlestick min price from point B})
  \]

This means the trade aims for a reward twice the distance between the max price at point **C** and the min price at point **B**. Here's how it maps to the strategy:

1. **Entry Level**: This defines where the trade will open, based on the identified high at point **C**.
2. **Stop Level**: This is the point at which the trade will exit to limit losses, based on the low at point **B**.
3. **Profit Level**: This sets the target price, aiming for a reward twice the risk, based on the difference between the highs and lows.


#### *Visual representation of a setup*
<img src="https://github.com/LoicL971/python_trade_runner/blob/main/images/setup.png" alt="Setup example" width="600" />

#### Initialize Backtest Object
```python
setup = Setup(0, pattern_list, trade_builder)

start = datetime(2022, 6, 15, tzinfo=timezone.utc)
end = datetime(2022, 6, 21, tzinfo=timezone.utc)
exchange = Exchange.BINANCE
symbol = Symbol.BTCUSDT
interval = Interval.M5

backtest = Backtest(
    setup_list=[setup],
    risk_for_setup_id={0: 0.01},
    start_datetime=start,
    end_datetime=end,
    window_size=150,
    initial_balance=1000,
    exchange=exchange,
    symbol=symbol,
    interval=interval,
    test_fees=False
)
```

### 4. Backtest your strategy
Run the backtest:
```python
backtest.initialize_chart()
backtest.step_until_end()
```

### 5. Analyze results 
After the backtest, analyze the results:
```python
print(f"Winrate: {b.get_results().get_winrate()}") # 0.5790671217292378
print(f"R ratio: {b.get_results().get_r()}") # 1.0
print(f"Max drawdown: {b.get_results().get_max_drawdown()}") # 0.36480565334278936
print(f"Expected profit per trade: {b.get_results().get_perf()}") # 0.01941314758239645
print(f"Succeeded trades: {b.get_results().get_nb_success()}") # 509
print(f"Stopped trades: {b.get_results().get_nb_stopped()}") # 370
print(f"Canceled trades: {b.get_results().get_nb_canceled()}") # 408
print(f"Final Balance: {b.balance}") # 1119.747233093188
```

#### Visualizations
- Plot balances:
```python
b.get_results().plot_balances()
```
<img src="https://github.com/LoicL971/python_trade_runner/blob/main/images/balances.png" alt="Plotted balances" width="600" />

- Show specific trades:
```python
b.get_results().show_some_archieved_trades(indexes=[25,26])
```
<img src="https://github.com/LoicL971/python_trade_runner/blob/main/images/trade.png" alt="Plotted trade" width="600" />

## License
This project is licensed under the MIT License. See the LICENSE.txt file for details.

## Acknowledgments
Special thanks to the open-source community for providing tools and inspiration for this project