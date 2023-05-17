#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import urllib.request
import pandas as pd
from test054_gid_helpers2 import *
import opengate_core as g4

paths = gate.get_default_test_paths(__file__, "", output="test055")

# bi213 83 213
# ac225 89 225
# fr221 87 221
# pb 82 212
z = 83
a = 213
nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)
print(nuclide)
sim_name = f"{nuclide.nuclide}_model"


def lc_read_csv(url):
    req = urllib.request.Request(url)
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0",
    )
    return pd.read_csv(urllib.request.urlopen(req))


livechart = "https://nds.iaea.org/relnsd/v0/data?"

df = lc_read_csv(livechart + "fields=decay_rads&nuclides=213bi&rad_types=x")
print(df)
# remove blanks (unknown intensities)
df = df[pd.to_numeric(df["intensity"], errors="coerce").notna()]
# convert to numeric. Note how one can specify the field by attribute or by string
df.energy = df["energy"].astype(float)
df.intensity = df["intensity"].astype(float)

pd.set_option("display.max_rows", None)  # Show all rows
pd.set_option("display.max_columns", None)  # Show all rows


print(df)

f, ax = plt.subplots(1, 1, figsize=(15, 5))
ax.bar(df.energy, df.intensity)

ax.legend()
# plt.show()
# f = paths.output / f"test054_{sim_name}.png"
# print("Save figure in ", f)
# plt.savefig(f)
plt.show()
