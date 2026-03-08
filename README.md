# 股票K线回放系统

基于 akshare + FastAPI 的股票数据后端，配合前端K线回放工具。

## 文件说明

- `kline-replay.html` - 前端K线回放页面
- `backend.py` - Python后端服务（FastAPI）
- `requirements.txt` - Python依赖包
- `start.bat` - Windows启动脚本
- `start.sh` - Linux/Mac启动脚本

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或者单独安装：
```bash
pip install fastapi uvicorn akshare pandas
```

### 2. 启动后端服务

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

或者直接运行：
```bash
python backend.py
```

服务启动后会显示：
```
========================================
股票数据后端服务
========================================
API文档: http://localhost:8000/docs
========================================
```

### 3. 打开前端

在浏览器中打开 `kline-replay.html` 文件。

前端会自动检测本地后端是否可用：
- 如果后端启动，优先使用 akshare 数据
- 如果后端未启动，自动降级使用东方财富API

## API接口

### 健康检查
```
GET /api/health
```

### 搜索股票
```
GET /api/search?keyword=平安银行
```

### 获取K线数据
```
GET /api/stock/kline?secid=0.000001&klt=101&fqt=1
```

参数说明：
- `secid`: 证券ID，格式 `市场.代码` (0=深市, 1=沪市)
- `klt`: K线类型 (101=日K, 102=周K, 103=月K)
- `fqt`: 复权类型 (0=不复权, 1=前复权, 2=后复权)

### 获取股票基础信息
```
GET /api/stock/info?secid=0.000001
```

## 使用示例

### Python代码示例

```python
import akshare as ak

# 获取平安银行日K数据（前复权）
df = ak.stock_zh_a_daily(
    symbol="sz000001",
    start_date="19910403",
    end_date="20231027",
    adjust="qfq"
)
print(df)

# 获取赛力斯基础信息
df = ak.stock_individual_basic_info_xq(symbol="SH601127")
print(df)
```

## 数据来源

- **本地后端**: akshare (从新浪/雪球等数据源爬取)
- **降级方案**: 东方财富公开API

## 注意事项

1. 首次运行时，akshare 可能需要几秒钟下载股票列表
2. 股票列表会缓存5分钟以提高性能
3. 请合理使用，避免频繁请求造成数据源压力
