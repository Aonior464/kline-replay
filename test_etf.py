#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试ETF相关接口
"""
import akshare as ak
from datetime import datetime

print("=" * 60)
print("测试ETF接口")
print("=" * 60)

# 测试1: 同花顺ETF实时行情
print("\n[测试1] fund_etf_spot_ths - 同花顺ETF实时行情")
print("-" * 60)
try:
    today_str = datetime.now().strftime("%Y%m%d")
    print(f"请求日期: {today_str}")
    df = ak.fund_etf_spot_ths(date=today_str)
    print(f"成功获取 {len(df)} 条ETF数据")
    print(df.head(10)[["基金代码", "基金名称"]])
except Exception as e:
    print(f"接口失败: {e}")

# 测试2: 新浪ETF历史行情
print("\n[测试2] fund_etf_hist_sina - 新浪ETF历史行情")
print("-" * 60)
try:
    symbol = "sh510050"  # 上证50ETF
    print(f"测试标的: {symbol}")
    df = ak.fund_etf_hist_sina(symbol=symbol)
    print(f"成功获取 {len(df)} 条K线数据")
    print(df.head())
    print("\n最后5条:")
    print(df.tail())
except Exception as e:
    print(f"接口失败: {e}")

# 测试3: 东方财富ETF历史行情（备用）
print("\n[测试3] fund_etf_hist_em - 东方财富ETF历史行情")
print("-" * 60)
try:
    code = "510050"
    print(f"测试标的: {code}")
    df = ak.fund_etf_hist_em(
        symbol=code,
        period="daily",
        start_date="20240101",
        end_date="20250101",
        adjust=""
    )
    print(f"成功获取 {len(df)} 条K线数据")
    print(df.head())
except Exception as e:
    print(f"接口失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
