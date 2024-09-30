
cvt_tf_rs = {
    'm': 'min',
    'h': 'H',
    'd': 'D',
    'w': 'W',
    'M': 'M',
}


def tf_to_resample(timeframe):
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    return f'{value}{cvt_tf_rs[unit]}'