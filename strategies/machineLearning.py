# -*- coding: utf-8 -*-
"""
Created on Sat Aug 19 11:06:44 2017

@author: Ivan Liu
"""


import pandas as pd
from pandas import DataFrame
import random
from copy import deepcopy
import math

# Backtrader
import backtrader as bt

# PyQuantTrader
from PyQuantTrader import strategy as pqt_strategy
from PyQuantTrader import validation as pqt_val
from PyQuantTrader import analyzers as pqt_ana
from PyQuantTrader import indicators as pqt_ind
from PyQuantTrader import observers as pqt_obs
from PyQuantTrader import sizers as pqt_sizers

# OandaAPI
import oandapy


# Strategy
class MyStrategy(bt.Strategy):  
    
    params = dict(
            hold = [8,8],
            )
    
    def notify_order(self, order):
        if order.status == order.Submitted:
            return

        dt, dn = self.datetime.datetime(), order.data._name
        print('{} {} Order {} Status {}'.format(
            dt, dn, order.ref, order.getstatusname())
        )

        whichord = ['main', 'stop', 'limit', 'close']
        
        if not order.alive():  # not alive - nullify
            dorders = self.o[order.data]
            idx = dorders.index(order)
            dorders[idx] = None
            print('-- No longer alive {} Ref'.format(whichord[idx]))

            if all(x is None for x in dorders):
                dorders[:] = []  # empty list - New orders allowed


    def log(self, txt, dt=None):  
        ''''' Logging function fot this strategy'''  
        dt = dt or self.datas[0].datetime.datetime(0)  
        print('%s, %s' % (dt.isoformat(), txt))  

    def __init__(self):  
        #self.sma1 = bt.indicators.SMA(self.data1.close, period=15)
        
        self.o = dict() # orders per data (main, stop, limit, manual-close)
        self.holding = dict() # holding periods per data
        kf = KalmanFilterInd()
        self.et, self.sqrt_qt, self.theta0, self.theta1 = kf.lines.et, kf.lines.sqrt_qt, kf.lines.theta0, kf.lines.theta1
        
    def start(self):  
        print("the world call me!")  
  
    def prenext(self):  
        print("not mature")  
  
    def next(self):  
        
        if self.et[0] < -self.sqrt_qt[0]:
            # Long entry
            action = 'long'
            size0 = 1
            size1 = self.theta0[0]
        elif self.et[0] > self.sqrt_qt[0]:
            # Short entry
            action = 'short'
            size0 = -self.theta0[0]
            size1 = -1
        elif self.et[0] > -self.sqrt_qt[0]:
            # Long exit
            action = 'longexit'
            size0 = -1
            size1 = -self.theta0[0]
        elif self.et[0] < self.sqrt_qt[0]:
            # Short exit
            action = 'shortexit'
            size0 = self.theta0[0]
            size1 = 1
        else:
            action = 'none'
            size0 = 0
            size1 = 0
            
        self.log('Kalman Filter: %s, %.4f, %.4f | et: %.4f, sqrt_qt: %.4f' % (action, size0, size1, self.et[0], self.sqrt_qt[0]))
        
#        for i, d in enumerate(self.datas):
#            dt, dn = self.datetime.datetime(), d._name
#            pos = self.getposition(d).size
#            print('{} {} Position {}'.format(dt, dn, pos))
#            
#            if not pos and not self.o.get(d, None):  # no market / no orders
#                self.o[d] = [self.buy(data=d)]
#                print('{} {} Buy {}'.format(dt, dn, self.o[d][0].ref))
#                self.holding[d] = 0
#                
#            elif pos:
#                self.holding[d] += 1
#                if self.holding[d] >= self.p.hold[i]:
#                    o = self.close(data=d)
#                    self.o[d].append(o)  # manual order to list of orders
#                    print('{} {} Manual Close {}'.format(dt, dn, o.ref))


# Sizer
class KalmanFilterSizer(bt.Sizer):
    """Proportion sizer"""
    params = {"prop": 0.1}
 
    def _getsizing(self, comminfo, cash, data, isbuy):
        """Returns the proper sizing"""
        target = self.broker.getvalue() * self.params.prop    # Ideal total value of the position
        price = data.close[0]
        qty = int(target / price)    # The actual number of shares bought
        if qty * price > cash:
            return 0    # Not enough money for this trade
        else:
            return qty
        # return self.broker.getposition(data).size    # Clear the position
        
        
# Indicators
class NumPy(object):
    packages = (('numpy', 'np'),)
    
class KalmanFilterInd(bt.Indicator, NumPy):
    _mindatas = 2  # needs at least 2 data feeds

    packages = ('pandas',)
    lines = ('et', 'sqrt_qt','theta0','theta1',)

    params = dict(
        delta=1e-4,
        vt=1e-3,
    )

    def __init__(self):
        self.wt = self.p.delta / (1 - self.p.delta) * np.eye(2)
        self.theta = np.zeros(2)
        self.P = np.zeros((2, 2))
        self.R = None

        self.d1_prev = self.data1(-1)  # data1 yesterday's price

    def next(self):
        F = np.asarray([self.data0[0], 1.0]).reshape((1, 2))
        y = self.d1_prev[0]

        if self.R is not None:  # self.R starts as None, self.C set below
            self.R = self.C + self.wt
        else:
            self.R = np.zeros((2, 2))

        yhat = F.dot(self.theta)
        et = y - yhat

        # Q_t is the variance of the prediction of observations and hence
        # \sqrt{Q_t} is the standard deviation of the predictions
        Qt = F.dot(self.R).dot(F.T) + self.p.vt
        sqrt_Qt = np.sqrt(Qt)

        # The posterior value of the states \theta_t is distributed as a
        # multivariate Gaussian with mean m_t and variance-covariance C_t
        At = self.R.dot(F.T) / Qt
        self.theta = self.theta + At.flatten() * et
        self.C = self.R - At * F.dot(self.R)

        # Fill the lines
        self.lines.et[0] = et
        self.lines.sqrt_qt[0] = sqrt_Qt
        self.lines.theta0[0] = self.theta[0]
        self.lines.theta1[0] = self.theta[1]
        

# Run Strategy
def runstrat(args=None):
    
    # csv data
    AUDUSD_df = pd.read_csv("../Common Data/fx_pairs/AUD_USD_M15.csv")
    AUDUSD_df = AUDUSD_df[['time', 'mid.o', 'mid.h', 'mid.l', 'mid.c', 'volume']]
    AUDUSD_df = AUDUSD_df.rename(columns={'mid.o': 'open', 'mid.h': 'high', 'mid.l': 'low', 'mid.c': 'close'})
    AUDUSD_df['openinterest'] = 0
    AUDUSD_df = AUDUSD_df.set_index('time')
    AUDUSD = bt.feeds.PandasData(dataname=AUDUSD_df) 
    
    USDCAD_df = pd.read_csv("../Common Data/fx_pairs/USD_CAD_M15.csv")
    USDCAD_df = USDCAD_df[['time', 'mid.o', 'mid.h', 'mid.l', 'mid.c', 'volume']]
    USDCAD_df = USDCAD_df.rename(columns={'mid.o': 'open', 'mid.h': 'high', 'mid.l': 'low', 'mid.c': 'close'})
    USDCAD_df['openinterest'] = 0
    USDCAD_df = USDCAD_df.set_index('time')
    USDCAD = bt.feeds.PandasData(dataname=USDCAD_df)
    
    n_cores = 4
    cash = 10000
    leverage = 20
    init_assets = cash * leverage
    positions = init_assets * 0.02
    
    # Initialize
    cerebro = bt.Cerebro(maxcpus=n_cores)
    
    # Data feed
    cerebro.adddata(AUDUSD, name ="AUDUSD")
    cerebro.adddata(USDCAD, name ="USDCAD")
    
    # Broker
    cerebro.broker.set_cash(init_assets)
    cerebro.broker.setcommission(0.0002)
        
    # Sizer
    cerebro.addsizer(KalmanFilterSizer)
    
    # Observer
    
    # Analyzer
    cerebro.addanalyzer(bt.analyzers.PyFolio)
    
    # Strategy
    cerebro.addstrategy(MyStrategy)
    
    # Execute
    strats = cerebro.run()
    
    # Report
    cerebro.plot()  
    
    strat0 = strats[0]
    pyfolio = strat0.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfolio.get_pf_items()
    # returns.to_csv('D:/Projects/PyQuantTrader/strategies/returns.csv')
    # positions.to_csv('D:/Projects/PyQuantTrader/strategies/positions.csv')
    # transactions.to_csv('D:/Projects/PyQuantTrader/strategies/transactions.csv')
    # gross_lev.to_csv('D:/Projects/PyQuantTrader/strategies/gross_lev.csv')
  
    # print('-- RETURNS')
    # print(returns)
    # print('-- POSITIONS')
    # print(positions)
    # print('-- TRANSACTIONS')
    # print(transactions)
    # print('-- GROSS LEVERAGE')
    print(gross_lev)

    import pyfolio as pf
    # PyFolio and backtrader
    pf.create_round_trip_tear_sheet(returns, positions, transactions)
    benchmark_rets = pd.Series([0.00004] * len(returns.index), index=returns.index)   
    pf.create_full_tear_sheet(returns, positions, transactions, benchmark_rets=benchmark_rets,
                              live_start_date='2017-07-10')

    
    
if __name__ == '__main__':  
    runstrat()
    