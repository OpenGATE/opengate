# Short Last Vertex water-dose test

```bash
python opengate/tests/src/actors/test094_last_vertex_splitting_rtplan_mt.py
```

Compares water-dose maps with and without LV, on one and four threads.
The four selected RTPlan intervals are repeated eight times. Each repetition
is a batch containing all its correlated replays; the variance of the mean
is the sample variance of the eight batch maps divided by eight.
For independent LV/reference seeds, each scored voxel must satisfy
`abs(D_LV - D_ref) / sqrt(var_LV + var_ref) <= 4`.
Both-zero voxels agree exactly. Unequal doses with zero variance fail.

Only public OpenGATE outputs are used. Dose maps stay in memory; only the
necessary temporary PHSP input is written. Checks also require completed
intervals, matching event/replay counts and finite, nonzero dose. The test
prints the maximum absolute Z-score and the number of voxels exceeding four
sigma. Low statistics and a repeated PHSP fixture limit this regression;
it is not a full physics or uncertainty validation.

The adjacent JSON contains numerical motion parameters from beam 0,
intervals 0/40/80/122 of the supplied local RTPlan and 32 real PHSP rows.
Its provenance retains the original plan hash and row indices, without
DICOM identity fields, isocentre coordinates or patient images. Rows were
selected among the first 512 by energy/(1+transverse radius) and are repeated
to give the same primary population per interval in mono and MT. Geometry
uses packaged Elekta Versa helpers, a water target, 4 cm shielding, 128
originals per interval and split 50. Seeds are 20261105 without LV and
20261106 with LV. No workspace files or external downloads are needed.
