## Additional functionalities

The command line tool ```opengate_user_info``` allo to print all default and possible parameters for Volumes, Sources, Physics and Actors elements. This is verbose but allow to have a dynamic documentation of everything currently available in the installed gate version.

The "contrib" folder contains additional functions that are useful but do not belong to the core of GATE.

The functions are used in several tests.

A readme file can be found : https://github.com/OpenGATE/opengate/tree/master/opengate/contrib/readme.md

### Dose rate computation

(documentation TODO), test035

### Linac : Elekta Synergy (warning: approximate model)

(documentation TODO), test019

### Phantom: IEC 6 spheres NEMA phantom

An analytical model of the 6 spheres IEC NEMA phantom is provided. It can be used as follows:

```python
import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec

sim = gate.Simulation()
iec_phantom = gate_iec.add_iec_phantom(sim)
```

The rotation should be adapted according to your need. The order of the 6 spheres can be changed with the parameter `sphere_starting_angle` of the `add_iec_phantom` command.

![](figures/iec_6spheres.png)

Example can be found in [test015](https://github.com/OpenGATE/opengate/blob/master/opengate/tests/src/test015_iec_phantom_1.py) (and others).


### Voxelization of the IEC 6 spheres phantom

(documentation TODO), test032

### Phantom: cylinder phantom for PET NECR

(documentation TODO), test037

### SPECT GE NM 670 (warning: approximate model)

(documentation TODO), test028

### SPECT "ideal reconstruction"

(documentation TODO)

### PET Philips Vereos

(documentation TODO), test037

## Source of gamma from ions decay

Several tools are provided to generate gammas from ions decay (GID = Gammas from Ions Decay).

Some command line tools (use '-h' option to get help):

```python
gid_info Ac225
```
Will generate :
```txt
Ac-225    Z=89 A=225     HL=10.0 d (864000.0 s)     BF=1.0
  Fr-221    Z=87 A=221     HL=4.9 m (294.0 s)     BF=1.0
    At-217    Z=85 A=217     HL=32.3 ms (0.0 s)     BF=1.0
      Bi-213    Z=83 A=213     HL=45.59 m (2735.4 s)     BF=0.99988
        Po-213    Z=84 A=213     HL=4.2 μs (0.0 s)     BF=0.9791
          Pb-209    Z=82 A=209     HL=3.253 h (11710.8 s)     BF=1.0
            Bi-209    Z=83 A=209     HL=stable (inf s)     BF=1.0
        Tl-209    Z=81 A=209     HL=2.161 m (129.7 s)     BF=0.0209
          Pb-209    Z=82 A=209     HL=3.253 h (11710.8 s)     BF=1.0
            Bi-209    Z=83 A=209     HL=stable (inf s)     BF=1.0
Nuclide: Ac-225, decay dataset: icrp107_ame2020_nubase2020
```

![](figures/Ac225_info.pdf)


```python
gid_info Ac225
```
Will generate :
```txt
Ac-225    Z=89 A=225     HL=10.0 d (864000.0 s)     BF=1.0
  Fr-221    Z=87 A=221     HL=4.9 m (294.0 s)     BF=1.0
    At-217    Z=85 A=217     HL=32.3 ms (0.0 s)     BF=1.0
      Bi-213    Z=83 A=213     HL=45.59 m (2735.4 s)     BF=0.99988
        Po-213    Z=84 A=213     HL=4.2 μs (0.0 s)     BF=0.9791
          Pb-209    Z=82 A=209     HL=3.253 h (11710.8 s)     BF=1.0
            Bi-209    Z=83 A=209     HL=stable (inf s)     BF=1.0
        Tl-209    Z=81 A=209     HL=2.161 m (129.7 s)     BF=0.0209
          Pb-209    Z=82 A=209     HL=3.253 h (11710.8 s)     BF=1.0
            Bi-209    Z=83 A=209     HL=stable (inf s)     BF=1.0
Nuclide: Ac-225, decay dataset: icrp107_ame2020_nubase2020
```

![](figures/Ac225_info.pdf)


```python
gid_tac Ac225
```

![](figures/Ac225_tac.pdf)


```python
gid_gammas Ac225
```

![](figures/Ac225_gammas.pdf)
