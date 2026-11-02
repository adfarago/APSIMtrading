"""The economic model and grid calculations from apsim_matlab_trading.mlx."""
from dataclasses import dataclass
import numpy as np

PROB = np.array([.15, .25, .25, .35])
PAYOFF = np.array([[1., 5., 3.], [1., 3., 5.], [1., 8., 4.], [1., 4., 8.]])
DELTA = np.array([.96, .96])
RISK = np.array([1.5, 2.5])
ASSETS = ('Bond', 'MFC', 'HFC')
INVESTORS = ('Mario', 'Hue')
INITIAL = np.array([[49., 0., 10., 0.], [49., 0., 0., 10.]])
GRID = 1001


def utility(x, risk):
    x = np.asarray(x, dtype=float)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        return (np.power(x, 1 - risk) - 1) / (1 - risk)


def consumption(holdings):
    return np.column_stack((holdings[:, 0], holdings[:, 1:] @ PAYOFF.T))


def reservation_prices(cons):
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        marginal = (cons[:, 1:] / cons[:, :1]) ** -RISK[:, None]
        return DELTA[:, None] * (marginal * PROB) @ PAYOFF


def total_utility(cons):
    return np.array([utility(cons[i, 0], RISK[i]) + DELTA[i] * np.sum(PROB * utility(cons[i, 1:], RISK[i])) for i in range(2)])


def proposed_utilities(cons, asset, direction, prices, amounts):
    """Utilities for Mario and Hue for broadcastable price and quantity arrays."""
    results = []
    with np.errstate(invalid='ignore', divide='ignore', over='ignore'):
        for i, sign in enumerate((direction, -direction)):
            now = cons[i, 0] - sign * prices * amounts
            future = sum(PROB[s] * utility(cons[i, s + 1] + sign * PAYOFF[s, asset] * amounts, RISK[i]) for s in range(4))
            results.append(utility(now, RISK[i]) + DELTA[i] * future)
    return results


def trade_range(cons, prices, asset):
    direction = np.sign(prices[0, asset] - prices[1, asset])
    mid = np.mean(prices[:, asset])
    base = total_utility(cons)
    maxdh, pick = 100., 0
    # MATLAB rescales until the last mutually beneficial trade is inside the grid.
    for _ in range(30):
        if not (pick < 10 or pick >= 989) or maxdh <= 1e-6:
            break
        maxdh = maxdh / 10 if pick < 10 else maxdh * 10
        dh = np.linspace(0, maxdh, GRID)
        v1, v2 = proposed_utilities(cons, asset, direction, mid, dh)
        good = np.flatnonzero((v1 >= base[0]) & (v2 >= base[1]))
        pick = int(good[-1]) if good.size else 0
    return dh, v1 - base[0], v2 - base[1], pick


def suggested_asset(cons, prices):
    gains = []
    quantities = []
    for asset in range(3):
        dh, dv1, dv2, _ = trade_range(cons, prices, asset)
        valid = (dv1 >= 0) & (dv2 >= 0)
        score = np.where(valid, dv1 + dv2, -np.inf)
        index = int(np.argmax(score))
        gains.append(score[index])
        quantities.append(dh[index])
    asset = int(np.argmax(gains))
    return asset, quantities[asset]


@dataclass
class Curves:
    asset: int
    direction: float
    pvec: np.ndarray
    dh: np.ndarray
    lines: list
    price: float
    amount: float


def suggested_amount(cons, asset, direction, p_mid, dh):
    v1, v2 = proposed_utilities(cons, asset, direction, p_mid, dh)
    dv1, dv2 = v1 - v1[0], v2 - v2[0]
    dv1 = np.where(dv1 < 0, -np.inf, dv1)
    dv2 = np.where(dv2 < 0, -np.inf, dv2)
    with np.errstate(divide='ignore', invalid='ignore'):
        score = dv1 / np.max(dv1) + dv2 / np.max(dv2)
    return dh[int(np.nanargmax(score))] if np.any(np.isfinite(score)) else 0.


def curves(cons, prices, asset, automatic_quantity=None):
    direction = np.sign(prices[0, asset] - prices[1, asset])
    low, high = sorted(prices[:, asset])
    spread = high - low
    margin = .5 if automatic_quantity is not None else .6
    pvec = np.linspace(low - margin * spread, high + margin * spread, GRID)
    dh0, _, _, pick = trade_range(cons, prices, asset)
    maxdh = (dh0[pick] if automatic_quantity is None else automatic_quantity) * 2.5
    if not np.isfinite(maxdh) or maxdh <= 0 or spread <= 1e-12:
        # Equal reservation prices or no mutually beneficial trade: avoid invalid axes.
        pvec = np.linspace(low - .01, high + .01, GRID)
        return Curves(asset, direction, pvec, np.linspace(0, 1, GRID), [np.full(GRID, np.nan)] * 4, (low + high) / 2, 0.)
    dh = np.linspace(0, maxdh, GRID)
    p = pvec[None, :]
    d = dh[:, None]
    v1, v2 = proposed_utilities(cons, asset, direction, p, d)
    b1, b2 = proposed_utilities(cons, asset, -direction, p, d)
    lines = []
    for v in (v1, b1, v2, b2):
        indexes = np.minimum(np.sum(v > v[0, :], axis=0), GRID - 1)
        line = dh[indexes].copy()
        line[(line == 0) | (line == maxdh)] = np.nan
        lines.append(line)
    amount = suggested_amount(cons, asset, direction, pvec[GRID // 2], dh)
    return Curves(asset, direction, pvec, dh, lines, (low + high) / 2, amount)


def execute(holdings, asset, price, amount):
    cons = consumption(holdings)
    direction = np.sign(reservation_prices(cons)[0, asset] - reservation_prices(cons)[1, asset])
    new = holdings.copy()
    new[0, asset + 1] += direction * amount
    new[1, asset + 1] -= direction * amount
    new[0, 0] -= direction * price * amount
    new[1, 0] += direction * price * amount
    if np.any(consumption(new) <= 0):
        raise ValueError('This trade would make consumption zero or negative. Choose a smaller trade.')
    return new


def execute_sequence(holdings, first, price, amount, count):
    """Execute the chosen trade, followed by the same suggestions as single trades.

    Return each intermediate utility for the history plot. If an automatic trade
    cannot proceed, retain the completed trades and report why the sequence ended.
    """
    new = holdings.copy()
    suggestion = first
    final_quantity = None
    history = []
    reason = ''
    for index in range(count):
        if index and (amount <= 0 or suggestion.direction == 0):
            reason = 'No further trade is suggested.'
            break
        try:
            new = execute(new, suggestion.asset, price, amount)
        except ValueError as exc:
            reason = str(exc)
            break
        cons = consumption(new)
        history.append(total_utility(cons))
        prices = reservation_prices(cons)
        asset, quantity = suggested_asset(cons, prices)
        low, high = sorted(prices[:, asset])
        spread = high - low
        direction = np.sign(prices[0, asset] - prices[1, asset])
        price = (low + high) / 2
        if not np.isfinite(quantity) or quantity <= 0 or spread <= 1e-12:
            amount = 0.
        else:
            p_mid = np.linspace(low - .5 * spread, high + .5 * spread, GRID)[GRID // 2]
            amount = suggested_amount(cons, asset, direction, p_mid, np.linspace(0, quantity * 2.5, GRID))
        # Intermediate trades only need the suggested values; plotting grids are
        # calculated once after the sequence, rather than once per trade.
        suggestion = Curves(asset, direction, None, None, [], price, amount)
        final_quantity = quantity
    if history:
        cons = consumption(new)
        suggestion = curves(cons, reservation_prices(cons), suggestion.asset, final_quantity)
    return new, history, suggestion, reason
