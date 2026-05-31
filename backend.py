#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票数据后端服务
使用 akshare 提供股票数据 API
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import akshare as ak
from Ashare import get_price as ashare_get_price
from typing import Optional, List, Dict, Any
import uvicorn
from datetime import datetime
import pandas as pd

app = FastAPI(title="股票数据API", version="1.0.0")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 缓存股票列表
_stock_list_cache = None
_etf_list_cache = None
_bond_list_cache = None
_index_list_cache = None
_list_cache_time = None

# 缓存训练股票池
_train_pool_cache = None
_train_pool_cache_time = None

# 内置常用ETF列表（作为后备）
BUILTIN_ETFS = [
    # AI/科技主线
    ("159819", "人工智能ETF"),
    ("159792", "芯片ETF"),
    ("562880", "科创芯片ETF"),
    ("512720", "计算机ETF"),
    ("515880", "通信ETF"),
    ("513180", "恒生科技ETF"),
    ("562500", "机器人ETF"),
    ("515230", "软件ETF"),
    ("512980", "传媒ETF"),
    # 新能源
    ("516160", "新能源ETF"),
    ("515790", "光伏ETF"),
    ("515030", "新能源车ETF"),
    ("159755", "电池ETF"),
    # 消费
    ("512690", "酒ETF"),
    ("159928", "消费ETF"),
    ("159996", "家电ETF"),
    ("515170", "食品饮料ETF"),
    # 医药
    ("159992", "创新药ETF"),
    ("512170", "医疗ETF"),
    # 周期
    ("512400", "有色金属ETF"),
    ("515220", "煤炭ETF"),
    ("512800", "银行ETF"),
    ("512880", "证券ETF"),
    ("515210", "钢铁ETF"),
    ("512200", "房地产ETF"),
    # 国防/资源
    ("512660", "军工ETF"),
    ("159611", "电力ETF"),
    ("516150", "稀土ETF"),
    ("159870", "化工ETF"),
    # 宽基指数
    ("510050", "上证50ETF"),
    ("510300", "沪深300ETF"),
    ("588000", "科创50ETF"),
    ("159915", "创业板ETF"),
    # 更多常用ETF
    ("159919", "沪深300ETF"),
    ("510500", "中证500ETF"),
    ("159922", "500ETF"),
    ("513500", "纳指ETF"),
    ("513100", "纳指ETF"),
    ("159985", "沪深300ETF"),
    ("518880", "黄金ETF"),
    ("159937", "黄金ETF"),
]


BUILTIN_INDICES = [
    ("000001", "上证指数", "1"),
    ("399001", "深证成指", "0"),
    ("399006", "创业板指", "0"),
    ("000300", "沪深300", "1"),
    ("000905", "中证500", "1"),
    ("000852", "中证1000", "1"),
    ("000016", "上证50", "1"),
    ("399303", "国证2000", "0"),
    ("000688", "科创50", "1"),
]


def get_all_symbols() -> pd.DataFrame:
    """获取A股股票+ETF+可转债+指数列表（带缓存）"""
    global _stock_list_cache, _etf_list_cache, _bond_list_cache, _index_list_cache, _list_cache_time
    # 缓存30分钟
    if (_list_cache_time is None or
        (datetime.now() - _list_cache_time).total_seconds() > 1800):
        # A股列表
        try:
            _stock_list_cache = ak.stock_info_a_code_name()
            print(f"A股列表: {len(_stock_list_cache)}只")
        except Exception as e:
            print(f"获取A股列表失败: {e}")
            if _stock_list_cache is None:
                _stock_list_cache = pd.DataFrame(columns=["code", "name"])

        # ETF列表
        try:
            try:
                etf_list = ak.fund_etf_spot_em()
                if etf_list is not None and not etf_list.empty and "代码" in etf_list.columns:
                    _etf_list_cache = etf_list[["代码", "名称"]].rename(columns={"代码": "code", "名称": "name"})
                    print(f"ETF列表: {len(_etf_list_cache)}只")
                else:
                    raise ValueError("ETF数据为空")
            except Exception as e1:
                print(f"东方财富ETF失败: {e1}")
                if _etf_list_cache is None:
                    _etf_list_cache = pd.DataFrame(BUILTIN_ETFS, columns=["code", "name"])
        except Exception as e:
            print(f"获取ETF失败: {e}")
            if _etf_list_cache is None:
                _etf_list_cache = pd.DataFrame(BUILTIN_ETFS, columns=["code", "name"])

        # 可转债列表
        try:
            bond_df = ak.bond_zh_cov()
            if bond_df is not None and not bond_df.empty:
                code_col = [c for c in bond_df.columns if "代码" in c]
                name_col = [c for c in bond_df.columns if ("简称" in c or "名称" in c) and "正股" not in c]
                if code_col and name_col:
                    _bond_list_cache = bond_df[[code_col[0], name_col[0]]].rename(
                        columns={code_col[0]: "code", name_col[0]: "name"})
                    _bond_list_cache["code"] = _bond_list_cache["code"].astype(str).str.zfill(6)
                    print(f"可转债列表: {len(_bond_list_cache)}只")
                else:
                    _bond_list_cache = pd.DataFrame(columns=["code", "name"])
            else:
                _bond_list_cache = pd.DataFrame(columns=["code", "name"])
        except Exception as e:
            print(f"获取可转债失败: {e}")
            if _bond_list_cache is None:
                _bond_list_cache = pd.DataFrame(columns=["code", "name"])

        # 指数列表（内置）
        _index_list_cache = pd.DataFrame(
            [(c, n) for c, n, _ in BUILTIN_INDICES], columns=["code", "name"])

        _list_cache_time = datetime.now()

    dfs = []
    for cache in [_stock_list_cache, _etf_list_cache, _bond_list_cache, _index_list_cache]:
        if cache is not None and not cache.empty:
            dfs.append(cache)
    if not dfs:
        return pd.DataFrame(BUILTIN_ETFS, columns=["code", "name"])
    return pd.concat(dfs, ignore_index=True)


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/search")
async def search_stock(keyword: str = Query(..., description="搜索关键词")):
    """
    搜索股票/ETF
    返回格式与东方财富API兼容
    """
    keyword = keyword.strip()
    if not keyword:
        return {"QuotationCodeTable": {"Data": []}}

    try:
        stock_list = get_all_symbols()

        # 搜索匹配
        mask = (stock_list["code"].str.contains(keyword, case=False, na=False) |
                stock_list["name"].str.contains(keyword, case=False, na=False))
        results = stock_list[mask].head(30)

        # 转换为东方财富格式
        index_codes = {c for c, _, _ in BUILTIN_INDICES}
        bond_codes = set()
        if _bond_list_cache is not None and not _bond_list_cache.empty:
            bond_codes = set(_bond_list_cache["code"].astype(str))
        data = []
        for _, row in results.iterrows():
            code = str(row["code"])
            name = row["name"]
            # 判断市场和secid
            if code in index_codes:
                idx_entry = next((c, n, m) for c, n, m in BUILTIN_INDICES if c == code)
                market = int(idx_entry[2])
                secid = f"{market}.{code}"
            elif code.startswith("6") or code.startswith("5"):
                market = 1
                secid = f"1.{code}"
            else:
                market = 0
                secid = f"0.{code}"

            data.append({
                "Name": name,
                "Code": code,
                "Market": market,
                "secid": secid,
                "Type": 14,
                "PinYin": ""
            })

        return {"QuotationCodeTable": {"Data": data}}

    except Exception as e:
        print(f"搜索失败: {e}")
        return {"QuotationCodeTable": {"Data": []}}


def resample_klines(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    将日K数据转换为周K或月K
    period: 'W'=周K, 'M'=月K
    """
    if df is None or df.empty:
        return df

    df = df.copy()
    # 确保日期列是datetime类型
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

    # 定义聚合规则
    agg_rules = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }
    # 如果有成交额也求和
    if "amount" in df.columns:
        agg_rules["amount"] = "sum"

    # 映射周期参数（兼容新版本pandas）
    pd_period = period
    if period == "W":
        pd_period = "W"
    elif period == "M":
        pd_period = "ME"  # Month End

    # 按周期聚合
    resampled = df.resample(pd_period).agg(agg_rules)
    resampled = resampled.dropna(subset=["open", "high", "low", "close"])

    # 重置索引，恢复date列
    resampled = resampled.reset_index()

    # 计算涨跌幅等指标
    if len(resampled) > 0:
        resampled["change_pct"] = 0.0
        resampled["change_amt"] = 0.0
        resampled["amplitude"] = 0.0

        for i in range(1, len(resampled)):
            prev_close = resampled.iloc[i - 1]["close"]
            curr_close = resampled.iloc[i]["close"]
            curr_high = resampled.iloc[i]["high"]
            curr_low = resampled.iloc[i]["low"]

            resampled.at[resampled.index[i], "change_amt"] = curr_close - prev_close
            if prev_close != 0:
                resampled.at[resampled.index[i], "change_pct"] = (curr_close - prev_close) / prev_close * 100
            if prev_close != 0:
                resampled.at[resampled.index[i], "amplitude"] = (curr_high - curr_low) / prev_close * 100

    # 格式化日期
    resampled["date"] = resampled["date"].dt.strftime("%Y-%m-%d")

    return resampled


def apply_forward_adjust(df):
    """
    对不复权数据做前复权处理。
    检测除权日（开盘价相对前一日收盘价的跳空比例异常），计算复权因子。
    """
    if df is None or df.empty or len(df) < 2:
        return df

    df = df.copy().reset_index(drop=True)

    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 从后往前累积复权因子
    factor = [1.0] * len(df)
    for i in range(len(df) - 1, 0, -1):
        prev_close = float(df.loc[i - 1, "close"])
        cur_open = float(df.loc[i, "open"])
        if prev_close <= 0:
            continue
        ratio = cur_open / prev_close
        # 除权特征：开盘/前收 跳空超过 8% 且不是正常涨跌停
        # 正常涨跌停的 ratio 在 [0.9, 1.1] 或 [0.8, 1.2] 范围内
        # ETF 分红通常导致 ratio < 0.97 的小幅跳空
        if ratio < 0.92:
            # 除权日，记录复权因子
            factor[i - 1] = factor[i] * ratio
        else:
            factor[i - 1] = factor[i]

    # 如果所有因子都是1，说明没有除权，直接返回
    if all(abs(f - 1.0) < 0.0001 for f in factor):
        return df

    # 应用复权因子（前复权：历史价格乘以因子）
    latest_factor = factor[-1]  # 最新的因子应该是1
    for i in range(len(df)):
        adj = factor[i] / latest_factor
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df.loc[i, col] = round(float(df.loc[i, col]) * adj, 4)

    return df


@app.get("/api/stock/kline")
async def get_kline(
    secid: str = Query(..., description="证券ID，格式: 1.600000 或 0.000001"),
    klt: int = Query(101, description="K线类型: 101=日K, 102=周K, 103=月K"),
    fqt: int = Query(1, description="复权类型: 0=不复权, 1=前复权, 2=后复权"),
    beg: str = Query("0", description="开始日期，格式: 20200101"),
    end: str = Query("20500101", description="结束日期，格式: 20250101")
):
    """
    获取K线数据（支持股票和ETF，支持日/周/月K）
    返回格式与东方财富API兼容
    """
    try:
        # 解析secid
        if "." in secid:
            _, code = secid.split(".", 1)
        else:
            code = secid

        # 解析日期 - 获取日K数据时用更早的开始日期，方便周期转换
        start_date = beg if beg != "0" else "19900101"
        end_date = end

        df = None
        # 尝试获取股票数据（优先用东方财富数据源，复权更准确）
        try:
            adjust_map = {0: "", 1: "qfq", 2: "hfq"}
            adjust = adjust_map.get(fqt, "qfq")

            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            if df is not None and not df.empty:
                col_map = {
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                    "振幅": "amplitude",
                    "涨跌幅": "change_pct",
                    "涨跌额": "change_amt",
                    "换手率": "turnover"
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        except Exception as e:
            print(f"东方财富股票数据获取失败，尝试新浪: {e}")
            try:
                if len(code) == 6:
                    symbol = f"sh{code}" if code.startswith("6") else f"sz{code}"
                else:
                    symbol = code
                df = ak.stock_zh_a_daily(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )
            except Exception as e2:
                print(f"新浪股票数据也失败，尝试ETF: {e2}")

        # 如果股票数据失败，尝试获取ETF数据
        if df is None or df.empty:
            try:
                # 优先使用东方财富ETF接口（支持前复权）
                df = ak.fund_etf_hist_em(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq" if fqt == 1 else ("hfq" if fqt == 2 else "")
                )
                if df is not None and not df.empty:
                    col_map = {
                        "日期": "date",
                        "开盘": "open",
                        "收盘": "close",
                        "最高": "high",
                        "最低": "low",
                        "成交量": "volume",
                        "成交额": "amount",
                        "振幅": "amplitude",
                        "涨跌幅": "change_pct",
                        "涨跌额": "change_amt",
                        "换手率": "turnover"
                    }
                    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            except Exception as e2:
                print(f"东方财富ETF接口失败，尝试新浪: {e2}")
                try:
                    if code.startswith("5") or code.startswith("6"):
                        sina_symbol = f"sh{code}"
                    else:
                        sina_symbol = f"sz{code}"
                    df = ak.fund_etf_hist_sina(symbol=sina_symbol)
                    if df is not None and not df.empty:
                        col_map = {"date": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}
                        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                        if "date" in df.columns:
                            df["date"] = pd.to_datetime(df["date"])
                            df = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]
                            df["date"] = df["date"].dt.strftime("%Y-%m-%d")
                except Exception as e3:
                    print(f"新浪ETF接口也失败: {e3}")

        if df is None or df.empty:
            return {"data": None}

        # 前复权处理：如果请求前复权但数据源不支持，手动计算
        if fqt == 1 and df is not None and not df.empty:
            df = apply_forward_adjust(df)

        # 根据klt参数转换周期
        if klt == 102:
            # 周K
            df = resample_klines(df, "W")
        elif klt == 103:
            # 月K
            df = resample_klines(df, "M")

        # 确保日期列是字符串格式
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        # 转换为东方财富格式
        klines = []
        prev_close_val = None
        for _, row in df.iterrows():
            # 格式: 日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
            date_str = row.get("date", "")
            open_price = float(row.get("open", 0) or 0)
            close = float(row.get("close", 0) or 0)
            high = float(row.get("high", 0) or 0)
            low = float(row.get("low", 0) or 0)
            volume = int(row.get("volume", 0) or 0)
            turnover = float(row.get("amount", 0) or 0)

            # 计算其他指标
            if prev_close_val is None:
                prev_close_val = close

            change_pct = float(row.get("change_pct", 0) or 0)
            if change_pct == 0 and prev_close_val:
                change_pct = ((close - prev_close_val) / prev_close_val * 100)

            change_amt = float(row.get("change_amt", 0) or 0)
            if change_amt == 0:
                change_amt = close - prev_close_val

            amplitude = float(row.get("amplitude", 0) or 0)
            if amplitude == 0 and prev_close_val:
                amplitude = ((high - low) / prev_close_val * 100) if prev_close_val else 0

            turnover_rate = float(row.get("turnover", 0) or 0)

            klines.append(
                f"{date_str},{open_price:.4f},{close:.4f},{high:.4f},{low:.4f},"
                f"{int(volume)},{turnover:.2f},{amplitude:.2f},{change_pct:.2f},"
                f"{change_amt:.4f},{turnover_rate:.2f}"
            )
            prev_close_val = close

        # 构建返回数据
        return {
            "data": {
                "code": code,
                "market": 1 if code.startswith("6") else 0,
                "name": "",
                "decimal": 2,
                "dktotal": len(klines),
                "klines": klines
            }
        }

    except Exception as e:
        print(f"获取K线失败: {e}")
        return {"data": None}


@app.get("/api/stock/info")
async def get_stock_info(secid: str = Query(..., description="证券ID")):
    """获取股票基础信息"""
    try:
        if "." in secid:
            _, code = secid.split(".", 1)
        else:
            code = secid

        # 雪球格式
        if code.startswith("6"):
            symbol = f"SH{code}"
        else:
            symbol = f"SZ{code}"

        df = ak.stock_individual_basic_info_xq(symbol=symbol)

        if df is not None and not df.empty:
            # 转换为字典
            info = df.set_index("item")["value"].to_dict()
            return {"data": info}

        return {"data": None}

    except Exception as e:
        print(f"获取股票信息失败: {e}")
        return {"data": None}


@app.get("/api/stock/flow")
async def get_money_flow(secid: str = Query(..., description="证券ID")):
    """获取资金流向（模拟数据，保持兼容性）"""
    try:
        return {
            "data": {
                "klines": []
            }
        }
    except Exception as e:
        return {"data": None}


@app.get("/api/train/pool")
async def get_train_pool():
    """
    获取随机训练股票池
    使用沪深300 + 中证500成分股（共~800只大市值A股）
    结果缓存24小时
    """
    global _train_pool_cache, _train_pool_cache_time

    # 24小时缓存
    if (_train_pool_cache is not None and
        _train_pool_cache_time is not None and
        (datetime.now() - _train_pool_cache_time).total_seconds() < 86400):
        return {"data": _train_pool_cache, "cached": True}

    try:
        pool = []
        seen_codes = set()

        # 获取沪深300 + 中证500成分股
        for index_code in ['000300', '000905']:
            index_label = 'hs300' if index_code == '000300' else 'csi500'
            try:
                df = ak.index_stock_cons_csindex(symbol=index_code)
                if df is not None and not df.empty:
                    # 列: 日期, 指数代码, 指数名称, 指数英文名称, 成分券代码, 成分券名称, 成分券英文名称, 交易所, 交易所英文名称
                    code_col = df.columns[4]  # 成分券代码
                    name_col = df.columns[5]  # 成分券名称
                    exchange_col = df.columns[7]  # 交易所

                    for _, row in df.iterrows():
                        code = str(row[code_col]).strip()
                        name = str(row[name_col]).strip()
                        exchange = str(row[exchange_col]).strip()

                        if code in seen_codes:
                            continue
                        # 排除ST
                        if 'ST' in name.upper():
                            continue

                        seen_codes.add(code)
                        # 判断市场: 6开头=沪市(1), 其他=深市(0)
                        mkt = "1" if code.startswith("6") else "0"
                        pool.append({
                            "code": code,
                            "name": name,
                            "mkt": mkt,
                            "secid": f"{mkt}.{code}",
                            "index": index_label,
                        })
                    print(f"指数 {index_code} 获取成功: {len(df)}只")
            except Exception as e:
                print(f"获取指数 {index_code} 成分股失败: {e}")

        if pool:
            _train_pool_cache = pool
            _train_pool_cache_time = datetime.now()
            print(f"训练股票池加载完成: {len(pool)}只")
        else:
            print("警告: 训练股票池为空")

        return {"data": pool, "cached": False}

    except Exception as e:
        print(f"获取训练股票池失败: {e}")
        return {"data": [], "error": str(e)}


@app.get("/api/stock/cap")
async def get_stock_cap(code: str = Query(..., description="股票代码，如600519")):
    """获取股票总市值（腾讯接口）"""
    import urllib.request
    try:
        prefix = "sh" if code.startswith("6") else "sz"
        url = f"https://qt.gtimg.cn/q={prefix}{code}"
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=5)
        data = resp.read().decode("gbk")
        parts = data.split("~")
        if len(parts) > 45 and parts[45]:
            cap_yi = float(parts[45])
            return {"data": {"总市值": cap_yi * 100000000}}
        return {"data": None}
    except Exception as e:
        print(f"获取市值失败 {code}: {e}")
        return {"data": None, "error": str(e)}


@app.get("/api/stock/profile")
async def get_stock_profile(code: str = Query(..., description="股票代码")):
    """获取公司基本信息（东方财富）"""
    import urllib.request
    import json as _json
    import gzip
    try:
        prefix = "SH" if code.startswith("6") else "SZ"
        url = f"https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code={prefix}{code}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://emweb.securities.eastmoney.com",
            "Accept-Encoding": "gzip",
        })
        resp = urllib.request.urlopen(req, timeout=8)
        raw = resp.read()
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        data = _json.loads(raw)
        if "jbzl" in data:
            j = data["jbzl"]
            f = data.get("fxxg", {})
            result = {
                "name": j.get("gsmc", ""),
                "eng_name": j.get("ywmc", ""),
                "industry": j.get("sshy", ""),
                "industry_detail": j.get("sszjhhy", ""),
                "exchange": j.get("ssjys", ""),
                "stock_type": j.get("zqlb", ""),
                "region": j.get("qy", ""),
                "chairman": j.get("frdb", ""),
                "gm": j.get("zjl", ""),
                "secretary": j.get("dm", ""),
                "employees": j.get("gyrs", ""),
                "reg_capital": j.get("zczb", ""),
                "website": j.get("gswz", ""),
                "address": j.get("bgdz", ""),
                "intro": j.get("gsjj", ""),
                "business": j.get("jyfw", ""),
                "list_date": f.get("ssrq", ""),
                "ipo_price": f.get("mgfxj", ""),
            }
            # 获取板块/概念
            try:
                board_url = f"https://datacenter.eastmoney.com/securities/api/data/get?type=RPT_F10_CORETHEME_BOARDTYPE&sty=BOARD_NAME,BOARD_CODE,BOARD_TYPE&filter=(SECURITY_CODE=%22{code}%22)&p=1&ps=50&sr=1&st=BOARD_CODE&token=894050c76af8597a853f5b408b759f5d"
                breq = urllib.request.Request(board_url, headers={"User-Agent": "Mozilla/5.0"})
                bresp = urllib.request.urlopen(breq, timeout=8)
                bdata = _json.loads(bresp.read())
                boards = bdata.get("result", {}).get("data", [])
                skip = {"HS300_", "央视50_", "上证50_", "上证180_", "MSCI中国", "富时罗素", "标准普尔", "融资融券", "沪股通", "深股通", "证金持股", "茅指数"}
                result["concepts"] = [b["BOARD_NAME"] for b in boards if not b.get("BOARD_TYPE") and b["BOARD_NAME"] not in skip and not b["BOARD_NAME"].endswith("_")]
                result["sectors"] = [b["BOARD_NAME"] for b in boards if b.get("BOARD_TYPE")]
            except Exception as e2:
                print(f"获取板块失败: {e2}")
                result["concepts"] = []
                result["sectors"] = []
            return {"data": result}
        return {"data": None}
    except Exception as e:
        print(f"获取公司信息失败 {code}: {e}")
        return {"data": None}


INDUSTRY_CHAIN = {
    "酿酒行业": {"up": ["高粱", "小麦", "水源", "酒曲", "包装材料", "玻璃瓶", "纸箱"], "mid": ["酿造", "勾调", "储存陈化", "灌装"], "down": ["白酒零售", "餐饮渠道", "商超", "电商", "礼品市场", "团购"]},
    "银行": {"up": ["央行货币政策", "同业拆借", "居民存款", "企业存款"], "mid": ["信贷业务", "理财产品", "支付结算", "信用卡"], "down": ["个人贷款", "企业贷款", "房贷", "消费金融"]},
    "证券": {"up": ["交易所", "监管政策", "资金来源"], "mid": ["经纪业务", "投行业务", "资管业务", "自营业务"], "down": ["散户投资者", "机构投资者", "上市企业"]},
    "保险": {"up": ["再保险", "资金池", "精算模型"], "mid": ["寿险", "财险", "健康险", "投资管理"], "down": ["个人客户", "企业客户", "银保渠道"]},
    "房地产": {"up": ["土地出让", "建材", "钢铁", "水泥", "设计院"], "mid": ["住宅开发", "商业地产", "物业管理"], "down": ["购房者", "租赁市场", "商业客户"]},
    "汽车": {"up": ["钢铁", "铝材", "芯片", "轮胎", "玻璃", "电池"], "mid": ["整车制造", "总装", "质检"], "down": ["4S店", "汽车经销", "出口", "网约车"]},
    "电力设备": {"up": ["铜材", "硅钢片", "绝缘材料", "稀土"], "mid": ["变压器", "开关设备", "电缆", "配电设备"], "down": ["电网公司", "新能源电站", "工业用户"]},
    "光伏": {"up": ["多晶硅", "银浆", "EVA胶膜", "玻璃"], "mid": ["硅片", "电池片", "组件", "逆变器"], "down": ["地面电站", "分布式光伏", "工商业屋顶"]},
    "电池": {"up": ["碳酸锂", "钴", "镍", "石墨", "电解液", "隔膜"], "mid": ["电芯制造", "PACK组装", "BMS"], "down": ["新能源车企", "储能电站", "两轮电动车"]},
    "半导体": {"up": ["硅片", "光刻胶", "特种气体", "靶材"], "mid": ["芯片设计", "晶圆制造", "封装测试"], "down": ["消费电子", "汽车电子", "通信设备", "工业控制"]},
    "消费电子": {"up": ["芯片", "面板", "电池", "结构件", "摄像头模组"], "mid": ["整机组装", "软件开发", "品牌运营"], "down": ["线上渠道", "线下门店", "运营商", "企业采购"]},
    "医药": {"up": ["原料药", "中药材", "辅料", "包装材料"], "mid": ["药品研发", "生产制造", "质量控制"], "down": ["医院", "药店", "线上药房", "基层医疗"]},
    "医疗器械": {"up": ["电子元器件", "塑料", "金属材料", "传感器"], "mid": ["设备制造", "体外诊断", "高值耗材"], "down": ["医院", "体检中心", "第三方检验"]},
    "食品饮料": {"up": ["农产品", "糖", "奶源", "包装材料"], "mid": ["食品加工", "饮料生产", "品牌营销"], "down": ["商超", "便利店", "电商", "餐饮"]},
    "家用电器": {"up": ["压缩机", "面板", "芯片", "钢板", "铜管"], "mid": ["产品设计", "生产制造", "品控"], "down": ["线下卖场", "电商平台", "工程渠道", "出口"]},
    "软件": {"up": ["云服务器", "开源框架", "数据库"], "mid": ["产品研发", "实施交付", "运维服务"], "down": ["政府", "金融", "制造业", "互联网企业"]},
    "计算机": {"up": ["芯片", "PCB", "存储器", "电源"], "mid": ["整机制造", "系统集成", "解决方案"], "down": ["政企客户", "教育", "医疗", "金融"]},
    "通信": {"up": ["芯片", "PCB", "光模块", "天线"], "mid": ["基站设备", "核心网", "传输设备"], "down": ["运营商", "企业专网", "数据中心"]},
    "互联网": {"up": ["云计算", "CDN", "服务器", "带宽"], "mid": ["平台运营", "内容生产", "广告系统"], "down": ["C端用户", "广告主", "商家"]},
    "钢铁": {"up": ["铁矿石", "焦炭", "废钢", "合金"], "mid": ["炼铁", "炼钢", "轧钢"], "down": ["建筑", "汽车", "机械", "家电", "造船"]},
    "化工": {"up": ["石油", "天然气", "煤炭", "矿产"], "mid": ["基础化工", "精细化工", "新材料"], "down": ["农业", "纺织", "建材", "电子"]},
    "军工": {"up": ["特种钢材", "复合材料", "电子元器件"], "mid": ["航空装备", "航天装备", "兵器装备", "船舶"], "down": ["国防建设", "军贸出口", "民用航空"]},
    "农林牧渔": {"up": ["种子", "饲料", "化肥", "农药", "农机"], "mid": ["种植", "养殖", "水产"], "down": ["食品加工", "批发市场", "商超", "出口"]},
    "旅游": {"up": ["交通基建", "地产物业", "餐饮供应链"], "mid": ["酒店运营", "景区运营", "旅行社"], "down": ["休闲旅客", "商务差旅", "会议会展"]},
    "传媒": {"up": ["IP版权", "内容创作", "技术平台"], "mid": ["影视制作", "游戏开发", "广告营销", "出版"], "down": ["院线", "流媒体", "广告主", "读者"]},
    "建筑": {"up": ["钢铁", "水泥", "玻璃", "工程机械"], "mid": ["设计", "施工", "装修"], "down": ["房地产", "基建", "工业厂房"]},
    "纺织服装": {"up": ["棉花", "化纤", "面料", "辅料"], "mid": ["纺纱", "织造", "印染", "成衣"], "down": ["品牌零售", "电商", "出口"]},
    "有色金属": {"up": ["矿石开采", "冶炼辅料", "能源"], "mid": ["冶炼", "精炼", "加工"], "down": ["电子", "新能源", "建筑", "航空航天"]},
    "煤炭": {"up": ["采矿设备", "爆破材料", "运输"], "mid": ["露天开采", "井下开采", "洗选加工"], "down": ["火电", "钢铁", "化工", "建材"]},
    "电力": {"up": ["煤炭", "天然气", "风机", "光伏组件"], "mid": ["火力发电", "风力发电", "水力发电", "核电"], "down": ["电网", "工商业用户", "居民用户"]},
    "环保": {"up": ["设备制造", "膜材料", "催化剂"], "mid": ["污水处理", "固废处理", "大气治理", "环境监测"], "down": ["政府项目", "工业企业", "市政设施"]},
    "物流": {"up": ["运输车辆", "仓储设施", "信息系统"], "mid": ["干线运输", "仓储管理", "配送", "供应链服务"], "down": ["电商", "制造业", "零售", "生鲜"]},
}


@app.get("/api/stock/chain")
async def get_stock_chain(code: str = Query(..., description="股票代码")):
    """获取产业链数据（行业模板+主营构成）"""
    import urllib.request
    import gzip
    import json as _json

    def _fetch_json(url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://emweb.securities.eastmoney.com", "Accept-Encoding": "gzip"})
        resp = urllib.request.urlopen(req, timeout=8)
        raw = resp.read()
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        return _json.loads(raw)

    try:
        prefix = "SH" if code.startswith("6") else "SZ"
        info = _fetch_json(f"https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code={prefix}{code}")
        industry = info.get("jbzl", {}).get("sshy", "")
        company = info.get("jbzl", {}).get("agjc", "")

        # 主营构成
        biz_products = []
        try:
            biz = _fetch_json(f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code={prefix}{code}")
            seen = set()
            for item in biz.get("zygcfx", []):
                if item.get("MAINOP_TYPE") == "2" and item.get("REPORT_DATE", "").startswith("202"):
                    ratio = item.get("MBI_RATIO", 0)
                    name = item.get("ITEM_NAME", "")
                    if ratio and ratio > 0.01 and name not in seen:
                        seen.add(name)
                        biz_products.append({"name": name, "ratio": round(ratio * 100, 1)})
        except Exception:
            pass

        # 匹配产业链模板
        chain = None
        for key in INDUSTRY_CHAIN:
            if key in industry or industry in key:
                chain = INDUSTRY_CHAIN[key]
                break

        return {"data": {
            "company": company,
            "industry": industry,
            "biz_products": biz_products[:6],
            "chain": chain,
        }}
    except Exception as e:
        print(f"产业链数据获取失败 {code}: {e}")
        return {"data": None}


def _to_ashare_code(secid: str) -> str:
    """将 secid (1.600519) 转为 Ashare 格式 (sh600519)"""
    if "." in secid:
        mkt, code = secid.split(".", 1)
    else:
        code = secid
        mkt = "1" if code.startswith("6") else "0"
    return ("sh" if mkt == "1" else "sz") + code


@app.get("/api/quote")
async def get_quote(secid: str = Query(..., description="证券ID")):
    """获取实时报价（最新1根日线）"""
    try:
        acode = _to_ashare_code(secid)
        df = ashare_get_price(acode, frequency='1d', count=1)
        if df is not None and not df.empty:
            row = df.iloc[-1]
            return {"data": {
                "close": float(row["close"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "volume": float(row["volume"]),
            }}
        return {"data": None}
    except Exception as e:
        print(f"实时报价失败: {e}")
        return {"data": None}


@app.get("/api/realtime/kline")
async def get_realtime_kline(
    secid: str = Query(..., description="证券ID，格式: 1.600519"),
    frequency: str = Query("15m", description="周期: 1m,5m,15m,30m,60m"),
    count: int = Query(48, description="获取根数")
):
    """获取实时分钟K线（盘中）"""
    try:
        acode = _to_ashare_code(secid)
        df = ashare_get_price(acode, frequency=frequency, count=count)
        if df is None or df.empty:
            return {"data": None}
        klines = []
        prev_close = None
        for idx, row in df.iterrows():
            time_str = idx.strftime("%Y-%m-%d %H:%M")
            o, c, h, l, v = float(row["open"]), float(row["close"]), float(row["high"]), float(row["low"]), float(row["volume"])
            chg_pct = ((c - prev_close) / prev_close * 100) if prev_close else 0
            chg_amt = (c - prev_close) if prev_close else 0
            amp = ((h - l) / prev_close * 100) if prev_close else 0
            klines.append(f"{time_str},{o:.2f},{c:.2f},{h:.2f},{l:.2f},{int(v)},0,{amp:.2f},{chg_pct:.2f},{chg_amt:.4f},0")
            prev_close = c
        return {"data": {"klines": klines, "code": secid}}
    except Exception as e:
        print(f"实时分钟线失败: {e}")
        return {"data": None}


@app.get("/api/etf/holdings")
async def get_etf_holdings(code: str = Query(..., description="ETF代码")):
    """获取ETF持仓占比"""
    import urllib.request
    import gzip
    import re
    try:
        url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=20&year=&month=&rt=0.123"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://fundf10.eastmoney.com"})
        resp = urllib.request.urlopen(req, timeout=8)
        raw = resp.read()
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        html = raw.decode("utf-8")
        rows = re.findall(
            r"<td>(\d+)</td><td><a[^>]*>(\d{6})</a></td><td[^>]*><a[^>]*>(.*?)</a></td>.*?<td class=['\"]tor['\"]>([\d.]+)%</td>",
            html, re.S
        )
        holdings = []
        for rank, stock_code, name, ratio in rows[:15]:
            holdings.append({"rank": int(rank), "code": stock_code, "name": name, "ratio": float(ratio)})
        return {"data": holdings}
    except Exception as e:
        print(f"获取ETF持仓失败 {code}: {e}")
        return {"data": []}


if __name__ == "__main__":
    print("=" * 50)
    print("股票数据后端服务")
    print("=" * 50)
    print("API文档: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
