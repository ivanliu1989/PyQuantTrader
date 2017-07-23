#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 23 15:24:37 2017

@author: Ivan Liu
"""

import backtrader as bt  

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
  