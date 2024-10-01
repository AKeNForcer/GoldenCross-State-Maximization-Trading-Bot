import pandas as pd
import numpy as np
from tqdm import tqdm
from scipy.stats import norm




def sliding_windows_random_sequence(data: pd.DataFrame,
                                    step: pd.Timestamp,
                                    lookback: pd.Timedelta | list[pd.Timedelta],
                                    n_seq=1, start_date=None,
                                    seed=42):
    if type(lookback) != list:
        lookback = [lookback]
    
    data = data.copy()
    data['r'] = data.pct_change().fillna(0)

    start_date = start_date or data.index[0]
    end_date = start_date + len(data) * data.index.freq


    res = pd.DataFrame(np.full((len(data), n_seq), np.nan),
                       index=pd.date_range(start_date,
                                           end_date - data.index.freq, 
                                           freq=data.index.freq))

    cnt = int(step / data.index.freq)
    
    np.random.seed(seed)

    for idx in tqdm(pd.date_range(start_date, end_date + data.index.freq, freq=step)):
        idx = np.min([idx, res.index[-1]])
        lb = np.random.choice(lookback)
        samples = data.loc[idx - lb + data.index.freq: idx]
        sel = slice(idx - (cnt - 1) * data.index.freq, idx)
        rnd = np.random.choice(samples['r'], (len(res.loc[sel]), n_seq))
        res.loc[sel] = rnd

    df_list = []

    for col in res.columns:
        df_list.append(pd.DataFrame({
            'close': (res[col] + 1).cumprod() * data['close'].iloc[0],
            'r': res[col]
        }, index=res.index))


    return df_list



def choice_random_sequence(data, n_seq=1, seed=42):
    data = data.copy()
    data['r'] = data.pct_change().fillna(0)

    np.random.seed(seed)

    res = np.random.choice(data['r'], (n_seq, len(data)))

    df_list = []
    for col in range(n_seq):
        df_list.append(pd.DataFrame({
            'close': (res[col] + 1).cumprod() * data['close'].iloc[0],
            'r': res[col]
        }, index=data.index))


    return df_list



def ind_norm_random_sequence(data, n_seq=1, seed=42):
    data = data.copy()
    data['r'] = data.pct_change().fillna(0)

    np.random.seed(seed)

    std = np.log(data['r'] + 1).std()
    res = norm(scale=std).rvs((n_seq, len(data)))
    res = np.exp(res) - 1

    df_list = []
    for col in range(n_seq):
        df_list.append(pd.DataFrame({
            'close': (res[col] + 1).cumprod() * data['close'].iloc[0],
            'r': res[col]
        }, index=data.index))


    return df_list



def variable_windows_random_sequence(data: pd.DataFrame,
                                     step: pd.Timestamp | list[pd.Timestamp],
                                     lookback: pd.Timedelta | list[pd.Timedelta],
                                     n_seq=1, start_date=None,
                                     seed=42):
    if type(step) != list:
        step = [step]
    if type(lookback) != list:
        lookback = [lookback]
    
    data = data.copy()
    data['r'] = data.pct_change().fillna(0)

    start_date = start_date or data.index[0]
    end_date = start_date + len(data) * data.index.freq


    res = pd.DataFrame(np.full((len(data), n_seq), np.nan),
                       index=pd.date_range(start_date,
                                           end_date - data.index.freq, 
                                           freq=data.index.freq))
    
    np.random.seed(seed)

    for k in tqdm(range(n_seq)):

        _last = start_date - data.index.freq
        step_list = []
        while _last < end_date:
            step_list.append(np.random.choice(step))
            _last += step_list[-1]

        step_list = pd.Series(step_list)
        idx_list = start_date - data.index.freq + step_list.cumsum()
        cut_idx = np.argmax(idx_list >= end_date)
        idx_list = np.clip(idx_list[:cut_idx+1], None, end_date)

        lookback_list = np.random.choice(lookback, len(step_list))

        for idx, st, lb in zip(idx_list, step_list, lookback_list):
            cnt = int(st / data.index.freq)
            samp_sel = np.random.choice(data.index[data.index > (start_date + lb)])
            samples = data.loc[samp_sel - lb : samp_sel]
            # print(samp_sel - lb, samp_sel)
            sel = slice(idx - (cnt - 1) * data.index.freq, idx)
            rnd = np.random.choice(samples['r'], (len(res.loc[sel])))
            res.loc[sel, k] = rnd

    df_list = []

    for col in res.columns:
        df_list.append(pd.DataFrame({
            'close': (res[col] + 1).cumprod() * data['close'].iloc[0],
            'r': res[col]
        }, index=res.index))


    return df_list