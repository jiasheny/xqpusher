# pysnowball

> 雪球APP Python API (需要自取token)
> 修改 [雪球股票数据接口 python edition](https://github.com/uname-yang/pysnowball.git)

## 修改内容
我想要监控雪球的组合实时仓位和调仓信息，方便跟单，这里在原有的项目上添加两个新的雪球组合接口，可以查看实时持仓和实时净值

## 快速指引

安装

```bash
git clone https://github.com/Pa55w0rd/pysnowball.git
cd pysnowball
pip install .
```

示例

```python
>>> import pysnowball as ball
>>> ball.set_token("xq_a_token=662745a236*****;u=909119****")
>>> ball.cash_flow('SH600000')
```

调用API前需要手动获取雪球网站的token,使用set_token设置token后才能访问雪球的API。s(xq_a_token & u)

传送门 === [如何获取雪球token](https://blog.crackcreed.com/diy-xue-qiu-app-shu-ju-api/)

## APIs
```python
>>> import pysnowball as ball
>>> dir(ball)
['__author__', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', 'api_ref', 'balance', 'blocktrans', 'bond', 'bonus', 'business', 'business_analysis', 'capital', 'capital_assort', 'capital_flow', 'capital_history', 'cash_flow', 'cons', 'convertible_bond', 'cube', 'earningforecast', 'f10', 'finance', 'fund', 'fund_achievement', 'fund_asset', 'fund_derived', 'fund_detail', 'fund_growth', 'fund_info', 'fund_manager', 'fund_nav_history', 'fund_trade_date', 'get_token', 'hkex', 'holders', 'income', 'index', 'index_basic_info', 'index_details_data', 'index_perf_30', 'index_perf_7', 'index_perf_90', 'index_weight_top10', 'indicator', 'industry', 'industry_compare', 'kline', 'main_indicator', 'margin', 'name', 'nav_daily', 'northbound_shareholding_sh', 'northbound_shareholding_sz', 'org_holding_change', 'os', 'pankou', 'quote_current', 'quote_detail', 'quotec', 'realtime', 'rebalancing_current', 'rebalancing_history', 'report', 'set_token', 'shareschg', 'skholder', 'skholderchg', 'suggest', 'suggest_stock', 'token', 'top_holders', 'user', 'utls', 'watch_list', 'watch_stock']
```
这里列出来的API都是雪球的API，具体调用方法请看[API文档](https://github.com/uname-yang/pysnowball/blob/master/README.md)

### 获取组合的实时净值
```python
import pysnowball as ball
ball.quote_current("ZHxx")
```

### 获取组合的仓位信息
```python
import pysnowball as ball
ball.rebalancing_current("ZHxx")
```

### 获取组合的调仓历史
```python
import pysnowball as ball
ball.rebalancing_history("ZHxx")
```
