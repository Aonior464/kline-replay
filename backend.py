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
        # 尝试获取股票数据
        try:
            # 补全代码前缀
            if len(code) == 6:
                if code.startswith("6"):
                    symbol = f"sh{code}"
                else:
                    symbol = f"sz{code}"
            else:
                symbol = code

            # 解析复权类型
            adjust_map = {0: "", 1: "qfq", 2: "hfq"}
            adjust = adjust_map.get(fqt, "qfq")

            df = ak.stock_zh_a_daily(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
        except Exception as e:
            print(f"股票数据获取失败，尝试ETF: {e}")

        # 如果股票数据失败，尝试获取ETF数据
        if df is None or df.empty:
            try:
                # 优先使用新浪ETF历史数据接口
                try:
                    # 构建新浪格式的symbol（sh510050 或 sz159915）
                    if code.startswith("5") or code.startswith("6"):
                        sina_symbol = f"sh{code}"
                    else:
                        sina_symbol = f"sz{code}"

                    df = ak.fund_etf_hist_sina(symbol=sina_symbol)

                    # 重命名列以匹配股票数据格式
                    if df is not None and not df.empty:
                        col_map = {
                            "date": "date",
                            "open": "open",
                            "high": "high",
                            "low": "low",
                            "close": "close",
                            "volume": "volume"
                        }
                        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

                        # 过滤日期范围
                        if "date" in df.columns:
                            df["date"] = pd.to_datetime(df["date"])
                            start_dt = pd.to_datetime(start_date)
                            end_dt = pd.to_datetime(end_date)
                            df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
                            df["date"] = df["date"].dt.strftime("%Y-%m-%d")
                except Exception as e_sina:
                    print(f"新浪ETF接口失败，尝试东方财富接口: {e_sina}")
                    # 降级到东方财富ETF接口
                    df = ak.fund_etf_hist_em(
                        symbol=code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq" if fqt == 1 else ""
                    )
                    # 重命名列以匹配股票数据格式
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
                print(f"ETF数据获取失败: {e2}")

        if df is None or df.empty:
            return {"data": None}

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


@app.get("/api/stock/info")
async def get_stock_info(code: str = Query(..., description="股票代码，如600519")):
    """获取单只股票基本信息（含总市值）"""
    try:
        df = ak.stock_individual_info_em(symbol=code)
        if df is None or df.empty:
            return {"data": None}
        info = {}
        for _, row in df.iterrows():
            info[str(row.iloc[0])] = row.iloc[1]
        return {"data": info}
    except Exception as e:
        print(f"获取股票信息失败 {code}: {e}")
        return {"data": None, "error": str(e)}


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


if __name__ == "__main__":
    print("=" * 50)
    print("股票数据后端服务")
    print("=" * 50)
    print("API文档: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
