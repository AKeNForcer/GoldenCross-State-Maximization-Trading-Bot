import numpy as np



def calc_precision(value, precision, roundfn=np.round):
    return roundfn(value / precision) * precision