import pandas as pd
import numpy as np



def preprocess_data(df: pd.DataFrame, freq: pd.Timedelta,
                    start_date: pd.Timestamp | None = None,
                    end_date: pd.Timestamp | None = None,
                    set_index=True):
    if set_index:
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)

    df = df[['close']]
    df = df.resample(freq).agg({ 'close': 'last' })
    df['close'] = df['close'].ffill()
    df.dropna(inplace=True)

    if start_date is not None:
        df = df.loc[df.index >= start_date]
    if end_date is not None:
        df = df.loc[df.index < end_date]

    return df



def sliding_window(arr, steps):
    return np.lib.stride_tricks.sliding_window_view(arr, window_shape=steps, axis=0)


def make_time_window(data, columns, steps, dropna=True):
    step_arr = sliding_window(data[columns].to_numpy(), steps)

    df = data.iloc[steps-1:].drop(columns=columns).copy()
    step_arr = pd.DataFrame(step_arr.reshape((step_arr.shape[0], -1)),
                            columns=[f"{c}[-{i}]" for c in columns for i in range(steps)],
                            index=df.index)
    
    df = pd.concat([df, step_arr], axis=1)

    if not dropna:
        df = df.join(data[[]], how='outer')

    return df