#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 23 09:35:03 2017

@author: Ivan Liu
"""

import backtrader as bt

class AcctValue(bt.Observer):
    alias = ('Value',)
    lines = ('value',)
 
    plotinfo = {"plot": True, "subplot": True}
 
    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue()    # Get today's account value (cash + stocks)
 
 