#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sat Jul 22 21:47:21 2017

@author: Ivan Liu
"""

from __future__ import (absolute_import, division, print_function,  
                        unicode_literals)  
  
import datetime  # For datetime objects  
import pandas as pd  
import backtrader as bt  
import numpy as np  
import PyQuantTrader.validation.walkforward as wfd
from copy import deepcopy
from pandas import Series, DataFrame
  
class ssa_index_ind(bt.Indicator):  
    lines = ('ssa',)  
    def __init__(self, ssa_window):  
        self.params.ssa_window = ssa_window  
        # 这个很有用，会有 not maturity生成  
        self.addminperiod(self.params.ssa_window * 2)  
  
    def get_window_matrix(self, input_array, t, m):  
        # 将时间序列变成矩阵  
        temp = []  
        n = t - m + 1  
        for i in range(n):  
            temp.append(input_array[i:i + m])  
        window_matrix = np.array(temp)  
        return window_matrix  
  
    def svd_reduce(self, window_matrix):  
        # svd分解  
        u, s, v = np.linalg.svd(window_matrix)  
        m1, n1 = u.shape  
        m2, n2 = v.shape  
        index = s.argmax()  # get the biggest index  
        u1 = u[:, index]  
        v1 = v[index]  
        u1 = u1.reshape((m1, 1))  
        v1 = v1.reshape((1, n2))  
        value = s.max()  
        new_matrix = value * (np.dot(u1, v1))  
        return new_matrix  
  
    def recreate_array(self, new_matrix, t, m):  
        # 时间序列重构  
        ret = []  
        n = t - m + 1  
        for p in range(1, t + 1):  
            if p < m:  
                alpha = p  
            elif p > t - m + 1:  
                alpha = t - p + 1  
            else:  
                alpha = m  
            sigma = 0  
            for j in range(1, m + 1):  
                i = p - j + 1  
                if i > 0 and i < n + 1:  
                    sigma += new_matrix[i - 1][j - 1]  
            ret.append(sigma / alpha)  
        return ret  
  
    def SSA(self, input_array, t, m):  
        window_matrix = self.get_window_matrix(input_array, t, m)  
        new_matrix = self.svd_reduce(window_matrix)  
        new_array = self.recreate_array(new_matrix, t, m)  
        return new_array  
  
    def next(self):  
        data_serial = self.data.get(size=self.params.ssa_window * 2)  
        self.lines.ssa[0] = self.SSA(data_serial, len(data_serial), int(len(data_serial) / 2))[-1]  
  
# Create a Stratey  
class MyStrategy(bt.Strategy):  
    params = (  
        ('ssa_window', 15),  
        ('maperiod', 15),  
    )  
  
    def log(self, txt, dt=None):  
        ''''' Logging function fot this strategy'''  
        dt = dt or self.datas[0].datetime.date(0)  
        print('%s, %s' % (dt.isoformat(), txt))  
  
    def __init__(self):  
        # Keep a reference to the "close" line in the data[0] dataseries  
        self.dataclose = self.datas[0].close  
  
        # To keep track of pending orders and buy price/commission  
        self.order = None  
        self.buyprice = None  
        self.buycomm = None  
  
        # Add a MovingAverageSimple indicator  
        self.ssa = ssa_index_ind(ssa_window=self.params.ssa_window, subplot=False)  
        # bt.indicator.LinePlotterIndicator(self.ssa, name='ssa')  
        self.sma = bt.indicators.SimpleMovingAverage(period=self.params.maperiod)  
    def start(self):  
        print("the world call me!")  
  
    def prenext(self):  
        print("not mature")  
  
    def notify_order(self, order):  
        if order.status in [order.Submitted, order.Accepted]:  
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do  
            return  
  
        # Check if an order has been completed  
        # Attention: broker could reject order if not enougth cash  
        if order.status in [order.Completed]:  
            if order.isbuy():  
                self.log(  
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %  
                    (order.executed.price,  
                     order.executed.value,  
                     order.executed.comm))  
  
                self.buyprice = order.executed.price  
                self.buycomm = order.executed.comm  
            else:  # Sell  
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %  
                         (order.executed.price,  
                          order.executed.value,  
                          order.executed.comm))  
  
            self.bar_executed = len(self)  
  
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:  
            self.log('Order Canceled/Margin/Rejected')  
  
        self.order = None  
  
    def notify_trade(self, trade):  
        if not trade.isclosed:  
            return  
  
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %  
                 (trade.pnl, trade.pnlcomm))  
  
    def next(self):  
        # Simply log the closing price of the series from the reference  
        self.log('Close, %.2f' % self.dataclose[0])  
  
        # Check if an order is pending ... if yes, we cannot send a 2nd one  
        if self.order:  
            return  
  
        # Check if we are in the market  
        if not self.position:  
  
            # Not yet ... we MIGHT BUY if ...  
            if self.dataclose[0] > self.ssa[0]:  
  
                # BUY, BUY, BUY!!! (with all possible default parameters)  
                self.log('BUY CREATE, %.2f' % self.dataclose[0])  
  
                # Keep track of the created order to avoid a 2nd order  
                self.order = self.buy()  
  
        else:  
  
            if self.dataclose[0] < self.ssa[0]:  
                # SELL, SELL, SELL!!! (with all possible default parameters)  
                self.log('SELL CREATE, %.2f' % self.dataclose[0])  
  
                # Keep track of the created order to avoid a 2nd order  
                self.order = self.sell()  
    def stop(self):  
        print("death")  
  
class AcctValue(bt.Observer):
    alias = ('Value',)
    lines = ('value',)
 
    plotinfo = {"plot": True, "subplot": True}
 
    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue()    # Get today's account value (cash + stocks)
 
 
class AcctStats(bt.Analyzer):
    """A simple analyzer that gets the gain in the value of the account; should be self-explanatory"""
 
    def __init__(self):
        self.start_val = self.strategy.broker.get_value()
        self.end_val = None
 
    def stop(self):
        self.end_val = self.strategy.broker.get_value()
 
    def get_analysis(self):
        return {"start": self.start_val, "end": self.end_val,
                "growth": self.end_val - self.start_val, "return": self.end_val / self.start_val}


if __name__ == '__main__':  
    
    # Walk forward
    tscv = TimeSeriesSplitImproved(10)
    split = tscv.split(dataframe, fixed_length=True, train_splits=2)
    
    walk_forward_results = list()
    # Be prepared: this will take a while
    for train, test in split:        
        # TRAINING
        trainer = bt.Cerebro(stdstats=False, maxcpus=1)
        trainer.broker.set_cash(1000000)
        trainer.broker.setcommission(0.02)
        trainer.addanalyzer(AcctStats)
        #trainer.addsizer(PropSizer)
        tester = deepcopy(trainer)
     
        trainer.addstrategy(MyStrategy)  
        
        data.tmp = bt.feeds.PandasData(dataname=dataframe.iloc[train]) 
        print(data.tmp)
        trainer.adddata(data.tmp)
        res = trainer.run()
        # Get optimal combination
            
        # TESTING
        tester.addstrategy(MyStrategy)    # Test with optimal combination
        data.tmp = bt.feeds.PandasData(dataname=dataframe.iloc[test])                                                                      # corresponds to testing
        tester.adddata(data.tmp)
     
        res = tester.run()
        res_dict = res[0].analyzers.acctstats.get_analysis()
        
        
        res_dict["start_date"] = dataframe.iloc[test[0]].name
        res_dict["end_date"] = dataframe.iloc[test[-1]].name
        walk_forward_results.append(res_dict)
    
    wfdf = DataFrame(walk_forward_results)
    wfdf