# Short Last Vertex run-transition test

Run from the OpenGATE repository root with its Python environment:

```bash
python opengate/tests/src/actors/test094_last_vertex_splitting_rtplan_mt.py
```

The `094` prefix groups this regression with the existing Last Vertex tests.
The entry point is discovered by `opengate_tests`; the `_helpers.py` module
is excluded by the runner's standard helper filter. Success uses `utility.test_ok`.
The test also runs from another working directory. It needs no workspace
simulation scripts, patient files, external PHSP, reference images or download.

The adjacent JSON fixture contains numerical motion parameters extracted with
the RTPlan reader from beam 0, intervals 0/40/80/122, of the supplied local
`rt_plan.dcm`, plus 32 real phase-space rows. Provenance records the original
plan SHA-256 and PHSP row indices. No DICOM identifiers, isocentre coordinates
or patient images are included. Selection ranks the first 512 rows of
`phsp_6.4MeV_sx_1.15_sy_0.8.root` by kinetic energy divided by one plus transverse
radius. Positions are in mm, energies in MeV and angles in degrees, as used by
the existing LINAC helpers. Repetition into a temporary ROOT tree gives the same
primary population in every interval for mono and MT despite the unchanged
native entry-start spacing. This repeated sample is for mechanics only.

The simulation uses the packaged Elekta Versa geometry/motion helpers, 4 cm
shielding, a water target, LV split 50, seed 20261105 and 128 original primaries
per interval. Two subprocesses test one and four workers. Assertions check
originals/replays against event statistics at every run boundary, aggregate
counts, generated/classified replay agreement, nonzero replay/dose and finite
dose/squared images. Native completion exercises the pending-replay guard;
queue getters are not exposed for direct Python inspection.

Dose sums, maximum absolute differences and exact equality are reported without
requiring mono/MT identity. A shared seed does not give identical random draws
across worker counts. Native debug traces estimate event spans and transition
gaps from flushed pipe arrival times, including observer overhead. The timing
condition is reported, not asserted: scheduling and occasional long replay
batches can change it. A first independent run took 6.9 seconds total and
generated 3 mono / 2 MT replays; one MT event span exceeded a transition gap.
This is neither a precise performance benchmark nor physics validation.

Temporary files are isolated per invocation and removed after score checks.
The report, fixture hash and plan provenance are printed to stdout.
