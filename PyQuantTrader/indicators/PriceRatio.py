#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 30 11:43:36 2017

@author: Ivan Liu
"""
import backtrader as bt  

class PriceRatio(bt.Indicator):
    _mindatas = 2
    
    packages = ('math',)
    lines = ('PriceRatio',)
    
    def __init__(self):
        self.AUDUSDclose = self.data0.close
        self.USDCADclose = self.data1.close
    
    def next(self):
        self.lines.PriceRatio[0] = math.log10(self.AUDUSDclose[0] / self.USDCADclose[0])