#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 23 15:30:48 2017

@author: Ivan Liu
"""
import backtrader as bt 
from PyQuantTrader import indicators as ind


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
        self.ssa = ind.ssa_index.ssa_index_ind(ssa_window=self.params.ssa_window, subplot=False)  
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
  