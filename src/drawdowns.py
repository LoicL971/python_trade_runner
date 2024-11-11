import numpy as np
import matplotlib.pyplot as plt
from time import time
from scipy.optimize import fsolve

def printall(coll):
    print(list(a for a in coll))

def get_random_binary_streak_sample(wr:float, trade_streak:int, sample_size:int):
    rng = np.random.default_rng()
    sample = np.array(rng.binomial(1, wr, trade_streak*sample_size))
    sample = np.reshape(sample, (sample_size, trade_streak))
    return sample

def mult_coeffs(sample:np.ndarray, risk, R):
    coeffs = (1 - sample)*(1-risk) + sample*(1+R*risk)
    return coeffs

def cum_mult(coeffs):
    balances = np.cumprod(coeffs, axis=1)
    return balances

def cum_max(balances):
    maxs = np.maximum.accumulate(balances, axis=1)
    return maxs

def max_drawdown_for_streak(balances, maxs):
    return np.max(np.maximum.accumulate(maxs-balances, axis=1)/maxs, axis=1)

def get_max_drawdowns(risk, wr, R, trade_streak, sample_size):
    sample = get_random_binary_streak_sample(wr, trade_streak, sample_size)
    coeffs = mult_coeffs(sample, risk, R)
    balances = cum_mult(coeffs)
    maxs = cum_max(balances)
    return max_drawdown_for_streak(balances, maxs)

def get_max_drawdowns2(risk, wr, R, trade_streak, sample_size):
    rng = np.random.default_rng()
    sample = np.array(rng.binomial(1, wr, trade_streak*sample_size))
    sample = np.reshape(sample, (sample_size, trade_streak))
    coeffs = (1 - sample)*(1-risk) + sample*(1+R*risk)
    balances = np.cumprod(coeffs, axis=1)
    maxs = np.maximum.accumulate(balances, axis=1)
    max_drawdowns = np.max(np.maximum.accumulate(maxs-balances, axis=1)/maxs, axis=1)
    return max_drawdowns

def get_percentile(likelihood, risk, wr, R, trade_streak, sample_size):
    max_drawdowns = get_max_drawdowns2(risk, wr, R, trade_streak, sample_size)
    return np.percentile(max_drawdowns, likelihood*100)

def risk_to_use(max_drawdown:float, wr:float, R:float, trade_streak:int, sample_size:int, likelihood:float):
    f = lambda x: get_percentile(likelihood, x, wr, R, trade_streak, sample_size)-max_drawdown
    risk = fsolve(f, 0.005)
    print(f"Percentile {get_percentile(likelihood, risk, wr, R, trade_streak, sample_size)}")
    return risk



max_drawdown = 0.20
t = time()
wr = 0.3815
R = 2.097
risk0 = 0.01
trade_streak = 1000
sample_size = 100000
likelihood = 0.70
# print(f"Percentile {get_percentile(0.9, risk, wr, R, trade_streak, sample_size)}")
risk = risk_to_use(max_drawdown, wr, R, trade_streak, sample_size, likelihood)[0]
print(f"Risk to use : {risk}")
plt.hist(get_max_drawdowns2(risk, wr, R, trade_streak, sample_size),bins='auto')
plt.show()

print(f"Time spent {time()-t}")
# np.random.Generator.binomial(1, wr, trade_streak)