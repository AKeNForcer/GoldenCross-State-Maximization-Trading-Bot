import pandas as pd
import numpy as np
from scipy.optimize import minimize



def samples_pdf(samples, bin_width, transform=None):
    samples = pd.Series(samples)

    if transform is None:
        transform = (lambda x: x, lambda x: x)
    trn, inv = transform
    
    pdf = np.round(trn(samples) / bin_width) * bin_width
    pdf = pdf.value_counts().sort_index() / samples.shape[-1]

    pdf.index = inv(pdf.index)

    return pdf


def maximize_return_points(ret, bound=(0.0, 1.0), fee=0, prev=None):
    if prev is None:
        prev = 0

    def objfn(fraction):
        return -(np.log(ret * fraction + 1 - np.abs((ret + 2) * (fraction - prev) * fee))).mean()
        # return -(np.log(ret * fraction + 1 - np.abs((ret + 2) * fraction * fee))).mean()

    result = minimize(objfn, x0=[0.5], bounds=[bound])

    return result.x[0]


def multi_assets_maximize_return_points(n_assets, samp_ret, samp_idx, bound=(0.0, 1.0), fee=0, prev=None):
    if prev is None:
        prev = np.full(n_assets + 1, 0)
        prev[-1] = 1

    def objfn(fraction):
        fraction = fraction[:-1]
        return -(np.log(fraction[samp_idx] * \
                        samp_ret + 1).mean() + \
                            np.log(1 - np.abs(fraction[samp_idx] - prev[samp_idx]) * 
                                   fee).mean())

    result = minimize(objfn, x0=np.full(n_assets + 1, 0.5), bounds=[bound] * (n_assets + 1),
                      constraints=({'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1}))

    return result.x[:-1]


def maximize_return(pdf, bound=(0.0, 1.0), fee=0):
    def objfn(fraction):
        return -(pdf * np.log(pdf.index  * fraction + 1 - np.abs((pdf.index + 2) * fraction * fee))).sum()

    result = minimize(objfn, x0=[0.5], bounds=[bound])

    return result.x[0]


def return_montecarlo(samples, period, n=1000, weight=None, freq=None):
    if weight is not None:
        weight = weight / np.sum(weight)
    n_period = int(period / (freq or samples.index.freq))
    rand_choice = np.random.choice(samples, (n, n_period), p=weight) + 1
    return rand_choice.prod(axis=-1) - 1


def calculate_fraction(start, df_train,
                       prd: pd.Timedelta = pd.to_timedelta('1day'),
                       nsamples: int = 10000,
                       iqr_ratio: float = 4,
                       nbins: int = 200,
                       transform=None,
                       weight=None):
    if transform is None:
        transform = (lambda x: x, lambda x: x)
    trn_ret = transform[0]

    df_train_sim = return_montecarlo(df_train, prd, nsamples, weight)
    binwidth = (trn_ret(np.quantile(df_train_sim, 0.75)) - \
                trn_ret(np.quantile(df_train_sim, 0.25))) * iqr_ratio / nbins

    pdf = samples_pdf(df_train_sim, binwidth, transform=transform)
    frac = maximize_return(pdf, bound=(0, 1.0), fee=0)
    return { 'time': start, 'fraction': frac }