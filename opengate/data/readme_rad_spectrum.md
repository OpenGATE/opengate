## Data for radionuclide spectra

### Beta spectrum

The file `rad_beta_spectrum.json` is generated using data from
[doseinfo-radar](https://www.doseinfo-radar.com/RADARDecay.html)
([direct link to the excel file](https://www.doseinfo-radar.com/BetaSpec.zip)).

Column C (n (MeV)) is used as energy bin edges with a prepend 0 (which is valid
because the step is constant and equal to the first value).
Column F (#/nt) is used as weights.
