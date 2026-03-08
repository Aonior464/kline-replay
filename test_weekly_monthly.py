#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试周K和月K转换功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend import resample_klines
import pandas as pd
from datetime import datetime

print("=" * 60)
print("测试周K/月K转换功能")
print("=" * 60)

# 创建模拟日K数据
print("\n[测试1] 创建模拟日K数据")
dates = pd.date_range(start='2024-01-01', end='2024-03-07', freq='B')
data = []
import random
base_price = 10.0
for d in dates:
    open_p = base_price + random.uniform(-0.5, 0.5)
    close_p = open_p + random.uniform(-1, 1)
    high_p = max(open_p, close_p) + random.uniform(0, 0.5)
    low_p = min(open_p, close_p) - random.uniform(0, 0.5)
    volume = random.randint(1000000, 10000000)
    data.append({
        'date': d.strftime('%Y-%m-%d'),
        'open': open_p,
        'high': high_p,
        'low': low_p,
        'close': close_p,
        'volume': volume
    })
    base_price = close_p

df_daily = pd.DataFrame(data)
print(f"日K数据: {len(df_daily)} 条")
print(df_daily.head())

print("\n[测试2] 转换为周K")
df_weekly = resample_klines(df_daily, 'W')
print(f"周K数据: {len(df_weekly)} 条")
print(df_weekly)

print("\n[测试3] 转换为月K")
df_monthly = resample_klines(df_daily, 'M')
print(f"月K数据: {len(df_monthly)} 条")
print(df_monthly)

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
