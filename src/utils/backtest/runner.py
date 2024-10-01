import pandas as pd
import numpy as np
from .backtest import backtest_by_weight


def weight_trade(data: pd.DataFrame,
                 get_weight,
                 get_weight_params: dict,
                 trade_freq: pd.Timedelta,
                 fee: float,
                 start_equity: float,
                 return_baseline_report=False):
    
    weight = get_weight(data.copy(), **get_weight_params)
    
    data = data[['close']].resample(trade_freq).last()
    
    data = data.join(weight[['weight']]).ffill().fillna(0)

    return backtest_by_weight(data['close'], data['weight'],
                              initial_cash=start_equity,
                              fees=fee,
                              return_baseline_report=return_baseline_report)



def robust_weight_trade(rand_sequence,
                        rand_sequence_args: dict,
                        get_weight,
                        get_weight_params: dict,
                        start_date: pd.Timestamp,
                        end_date: pd.Timestamp,
                        trade_freq: pd.Timedelta,
                        fee: float,
                        start_equity: float,
                        verbose=True):
    
    test_df_list = rand_sequence(**rand_sequence_args)

    run_results = []
    run_report = []
    run_baseline_report = []

    for i, dd in enumerate(test_df_list):
        if verbose: print(F'=== RUN {i+1} ===')
        results, report, baseline_report = weight_trade(
            data=dd,
            get_weight=get_weight,
            get_weight_params=get_weight_params,
            start_date=start_date,
            end_date=end_date,
            trade_freq=trade_freq,
            fee=fee,
            start_equity=start_equity,
            return_baseline_report=True
        )

        run_results.append(results)
        run_report.append(report)
        run_baseline_report.append(baseline_report)
    
    run_report = pd.DataFrame(run_report, index=range(len(run_report)))
    run_baseline_report = pd.DataFrame(run_baseline_report, index=range(len(run_baseline_report)))

    run_report.columns = pd.MultiIndex.from_tuples([('strategy', col) for col in run_report.columns])
    run_baseline_report.columns = pd.MultiIndex.from_tuples([('baseline', col) for col in run_baseline_report.columns])

    return run_results, pd.concat([run_report, run_baseline_report], axis=1).swaplevel(0, 1, axis=1).sort_index(axis=1)




def weight_trade_with_idx(idx, *args, **kwargs):
    _, report = weight_trade(*args, **kwargs)
    return idx, report
