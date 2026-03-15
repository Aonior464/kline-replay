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


def get_all_symbols() -> pd.DataFrame:
    """获取A股股票+ETF列表（带缓存）"""
    global _stock_list_cache, _etf_list_cache, _list_cache_time
    # 缓存5分钟
    if (_stock_list_cache is None or
        _etf_list_cache is None or
        _list_cache_time is None or
        (datetime.now() - _list_cache_time).total_seconds() > 300):
        try:
            # 获取A股列表
            try:
                _stock_list_cache = ak.stock_info_a_code_name()
            except Exception as e:
                print(f"获取A股列表失败: {e}")
                _stock_list_cache = pd.DataFrame(columns=["code", "name"])

            # 获取ETF列表
            try:
                # 优先使用同花顺ETF实时行情接口
                try:
                    from datetime import datetime as dt
                    today_str = dt.now().strftime("%Y%m%d")
                    etf_list = ak.fund_etf_spot_ths(date=today_str)
                    if etf_list is not None and not etf_list.empty:
                        # 重命名列以匹配股票格式
                        if "基金代码" in etf_list.columns and "基金名称" in etf_list.columns:
                            etf_list = etf_list[["基金代码", "基金名称"]].rename(columns={"基金代码": "code", "基金名称": "name"})
                            # 确保基金代码是6位字符串
                            etf_list["code"] = etf_list["code"].astype(str).str.zfill(6)
                            _etf_list_cache = etf_list
                        else:
                            raise ValueError("同花顺ETF数据列名不匹配")
                    else:
                        raise ValueError("同花顺ETF数据为空")
                except Exception as e_ths:
                    print(f"同花顺ETF接口失败，尝试东方财富接口: {e_ths}")
                    # 降级到东方财富ETF接口
                    etf_sh = ak.fund_etf_spot_em()
                    if etf_sh is not None and not etf_sh.empty:
                        # 重命名列以匹配股票格式
                        if "代码" in etf_sh.columns and "名称" in etf_sh.columns:
                            etf_sh = etf_sh[["代码", "名称"]].rename(columns={"代码": "code", "名称": "name"})
                            _etf_list_cache = etf_sh
                        else:
                            etf_sh = pd.DataFrame(columns=["code", "name"])
                            _etf_list_cache = etf_sh
                    else:
                        etf_sh = pd.DataFrame(columns=["code", "name"])
                        _etf_list_cache = etf_sh
            except Exception as e:
                print(f"获取ETF列表失败，使用内置列表: {e}")
                # 使用内置ETF列表
                _etf_list_cache = pd.DataFrame(BUILTIN_ETFS, columns=["code", "name"])

            _list_cache_time = datetime.now()
        except Exception as e:
            print(f"获取列表失败: {e}")
            # 失败时至少返回内置ETF
            return pd.DataFrame(BUILTIN_ETFS, columns=["code", "name"])

    # 合并股票和ETF
    dfs = []
    if not _stock_list_cache.empty:
        dfs.append(_stock_list_cache)
    if not _etf_list_cache.empty:
        dfs.append(_etf_list_cache)
    # 如果都为空，使用内置ETF
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
        data = []
        for _, row in results.iterrows():
            code = row["code"]
            name = row["name"]
            # 判断市场
            if code.startswith("6"):
                market = 1  # 沪市
                secid = f"1.{code}"
            else:
                market = 0  # 深市
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


@app.get("/api/quote")
async def get_quote(secid: str = Query(..., description="证券ID")):
    """获取实时报价（模拟数据）"""
    try:
        return {"data": None}
    except Exception as e:
        return {"data": None}


if __name__ == "__main__":
    print("=" * 50)
    print("股票数据后端服务")
    print("=" * 50)
    print("API文档: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
