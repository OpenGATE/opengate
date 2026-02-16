import numpy as np
from typing import Literal, Union, Sequence

from bisect import bisect_right


def polynomial_map(x, coeffs):
    return np.polyval(coeffs, x)


ExtrapMode = Literal["raise", "clip", "extrapolate", "nan"]


def piecewise_linear_interpolation(
    x: float,
    x_lut: Sequence[float],
    y_lut: Sequence[float],
    *,
    extrapolation: ExtrapMode = "raise",
) -> Union[float, float]:
    """
    Piecewise linear interpolation based on a lookup table (LUT).

    Parameters
    ----------
    x : float
        Query point.
    x_lut : Sequence[float]
        Monotonically increasing x values (length >= 2).
    y_lut : Sequence[float]
        Corresponding y values; must be same length as x_lut.
    extrapolation : {'raise', 'clip', 'extrapolate', 'nan'}, optional
        Behavior when x is outside [x_lut[0], x_lut[-1]]:
        - 'raise': raise ValueError (default)
        - 'clip': use y at nearest endpoint
        - 'extrapolate': linear extrapolation using the nearest segment
        - 'nan': return float('nan')

    Returns
    -------
    float
        Interpolated (or extrapolated) y value.

    Notes
    -----
    - If x exactly equals an x_lut node, the corresponding y is returned.
    - For x in (x_i, x_{i+1}), linear interpolation is performed.
    """
    if len(x_lut) != len(y_lut):
        raise ValueError("x_lut and y_lut must have the same length.")
    if len(x_lut) < 2:
        raise ValueError("x_lut and y_lut must contain at least two points.")
    if any(x_lut[i] >= x_lut[i + 1] for i in range(len(x_lut) - 1)):
        raise ValueError("x_lut must be strictly increasing.")

    # Fast path: exact node match
    # (Optional: if duplicates existed, we could choose a policy, but we disallow them)
    # Handle out-of-bounds
    x0, xN = x_lut[0], x_lut[-1]
    if x < x0:
        if extrapolation == "raise":
            raise ValueError(f"x={x} is less than the minimum x_lut={x0}.")
        elif extrapolation == "clip":
            return y_lut[0]
        elif extrapolation == "nan":
            return float("nan")
        elif extrapolation == "extrapolate":
            i = 0  # use first segment [0,1]
        else:
            raise ValueError(f"Unknown extrapolation mode: {extrapolation}")
    elif x > xN:
        if extrapolation == "raise":
            raise ValueError(f"x={x} is greater than the maximum x_lut={xN}.")
        elif extrapolation == "clip":
            return y_lut[-1]
        elif extrapolation == "nan":
            return float("nan")
        elif extrapolation == "extrapolate":
            i = len(x_lut) - 2  # use last segment [N-2, N-1]
        else:
            raise ValueError(f"Unknown extrapolation mode: {extrapolation}")
    else:
        # x in [x0, xN]
        # Find right insertion point; we want i such that x in [x_i, x_{i+1}]
        j = bisect_right(x_lut, x)
        if j == 0:
            i = 0
        elif j == len(x_lut):
            # x == x_lut[-1]
            return y_lut[-1]
        else:
            i = j - 1
            # If exactly equals left node, return exact y
            if x == x_lut[i]:
                return y_lut[i]

    x_i, x_ip1 = x_lut[i], x_lut[i + 1]
    y_i, y_ip1 = y_lut[i], y_lut[i + 1]

    # Linear interpolation
    t = (x - x_i) / (x_ip1 - x_i)  # in [0,1] for interior points
    y = y_i + t * (y_ip1 - y_i)
    return y
