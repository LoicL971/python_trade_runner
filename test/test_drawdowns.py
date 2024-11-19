import pytest

from python_trade_runner import risk_to_use

def test_drawdown():
    max_drawdown = 0.20
    wr = 0.4
    R = 2.00
    trade_streak = 100
    sample_size = 1000
    likelihood = 0.70

    risk = risk_to_use(max_drawdown, wr, R, trade_streak, sample_size, likelihood)[0]
    assert risk == pytest.approx(0.0181, abs=1e-3)
