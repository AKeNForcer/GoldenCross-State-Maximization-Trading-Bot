import numpy as np



def calc_precision(value, precision, roundfn=np.round):
    return roundfn(value / precision) * precision



def validate_precision(value, precision):
    mul = int(value / precision)

    if value == mul * precision:
        return True
    if value == (mul + 1) * precision:
        return True
    
    return False
    
