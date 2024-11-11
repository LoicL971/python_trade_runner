import numpy as np
import matplotlib.pyplot as plt
from time import time
from scipy.optimize import fsolve
from src.python_trade_runner import risk_to_use, get_max_drawdowns2

max_drawdown = 0.20
t = time()
wr = 0.3815
R = 2.097
trade_streak = 1000
sample_size = 10000
likelihood = 0.70
risk = risk_to_use(max_drawdown, wr, R, trade_streak, sample_size, likelihood)[0]
print(f"Risk to use : {risk}")
plt.hist(get_max_drawdowns2(risk, wr, R, trade_streak, sample_size),bins='auto')
plt.show()

print(f"Time spent {time()-t}")
