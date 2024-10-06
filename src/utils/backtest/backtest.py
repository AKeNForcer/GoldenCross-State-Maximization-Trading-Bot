#Usual Suspects
import pandas as pd
import numpy as np
import vectorbt as vbt




def handle_nan(x, ifnan=None, ifinf=None):
    if np.isnan(x) and ifnan:
        return ifnan
    if np.isinf(x) and ifnan:
        return ifinf
    
    return x




def annual_return(eq, annual_ratio=None):
    annual_ratio = annual_ratio or (365 * pd.to_timedelta('1day') / eq.index.freq)
    ret = np.log(eq.pct_change().fillna(0) + 1) * annual_ratio
    return ret

def avg_annual_return_percent(eq, annual_ratio=None):
    return 100 * (np.exp(np.mean(annual_return(eq, annual_ratio))) - 1)

def std_annual_return_percent(eq, annual_ratio=None):
    return 100 * (np.exp(np.std(annual_return(eq, annual_ratio))) - 1)

def log_shape_ratio(eq, annual_ratio=None):
    ret = annual_return(eq, annual_ratio)
    std = ret.std()
    if std == 0:
        return np.nan
    return ret.mean() / std



def backtest_by_weight(data: pd.DataFrame | pd.Series,
                       weights: pd.DataFrame | pd.Series,
                       initial_cash=1_000, fees=0.001,
                       freq=None, include_baseline=True,
                       return_baseline_report=False,
                       annual_ratio=None):
    res = {}

    # Create a Portfolio object
    strategy_port = vbt.Portfolio.from_orders(
        close=data,
        size=weights,
        size_type='targetpercent',
        freq=freq or data.index.freq,  # Daily rebalancing
        init_cash=initial_cash,
        fees=fees  # Set transaction fees (optional)
    )
    res['strategy_equity'] = strategy_port.value()
    strategy_report = strategy_port.stats()
    strategy_report['Avg. Annual Return [%]'] = avg_annual_return_percent(res['strategy_equity'], annual_ratio)
    strategy_report['Std. Annual Return [%]'] = std_annual_return_percent(res['strategy_equity'], annual_ratio)
    strategy_report['Log Sharpe Ratio'] = log_shape_ratio(res['strategy_equity'], annual_ratio)

    if include_baseline:
        sz = np.full(len(data), 1)
        sz[-1] = 0
        baseline_port = vbt.Portfolio.from_orders(
            close=data,
            size=sz,
            freq=freq or data.index.freq,  # Daily rebalancing
            init_cash=initial_cash,
            fees=fees  # Set transaction fees (optional)
        )
        res['baseline_equity'] = baseline_port.value()
        baseline_report = baseline_port.stats()
        baseline_report['Avg. Annual Return [%]'] = avg_annual_return_percent(res['baseline_equity'], annual_ratio)
        strategy_report['Std. Annual Return [%]'] = std_annual_return_percent(res['strategy_equity'], annual_ratio)
        strategy_report['Log Sharpe Ratio'] = log_shape_ratio(res['strategy_equity'], annual_ratio)


    if return_baseline_report:
        return pd.DataFrame(res), strategy_report, baseline_report
    
    return pd.DataFrame(res), strategy_report

