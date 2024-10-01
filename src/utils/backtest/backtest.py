#Usual Suspects
import pandas as pd
import numpy as np
import vectorbt as vbt





def annual_return(eq, annual_ratio=None):
    annual_ratio = annual_ratio or (365 * pd.to_timedelta('1day') / eq.index.freq)
    ret = np.log(eq.pct_change().fillna(0) + 1) * annual_ratio
    return 100 * (np.exp(np.mean(ret)) - 1)



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
    strategy_report['Annual Return [%]'] = annual_return(res['strategy_equity'], annual_ratio)

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
        baseline_report['Annual Return [%]'] = annual_return(res['baseline_equity'], annual_ratio)


    if return_baseline_report:
        return pd.DataFrame(res), strategy_report, baseline_report
    
    return pd.DataFrame(res), strategy_report

