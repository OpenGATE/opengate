def ene_win_peak(name, energy, energy_width_percent):
    energy_width_percent = energy * energy_width_percent / 2
    e_min = energy - energy_width_percent
    e_max = energy + energy_width_percent
    a = {"name": name, "min": e_min, "max": e_max}
    return a


def ene_win_down_scatter(name, peak_min_value, energy_width_percent):
    e_max = peak_min_value
    e_min = e_max / (1 + energy_width_percent / 2)
    a = {"name": name, "min": e_min, "max": e_max}
    return a


def ene_win_up_scatter(name, peak_max_value, energy_width_percent):
    e_min = peak_max_value
    e_max = e_min / (1 - energy_width_percent / 2)
    a = {"name": name, "min": e_min, "max": e_max}
    return a


def energy_windows_peak_scatter(
    peak_name,
    down_scatter_name,
    up_scatter_name,
    peak,
    peak_width,
    down_scatter_width,
    up_scatter_width=None,
):
    if up_scatter_width is None:
        up_scatter_width = down_scatter_width
    p = ene_win_peak(peak_name, peak, peak_width)
    do = ene_win_down_scatter(down_scatter_name, p["min"], down_scatter_width)
    up = ene_win_up_scatter(up_scatter_name, p["max"], up_scatter_width)
    return do, p, up
