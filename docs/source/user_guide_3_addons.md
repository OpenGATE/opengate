## Additional functionalities

The command line tool ```opengate_user_info``` allows you to print all default and possible parameters for Volumes, Sources, Physics and Actors elements. This is verbose, but it allows you to have a dynamic documentation of everything currently available in the installed gate version.

The "contrib" folder contains additional functions that are useful, but do not belong to the core of GATE.

The functions are used in several tests.

A readme file can be found : https://github.com/OpenGATE/opengate/tree/master/opengate/contrib/readme.md

### Dose rate computation

(documentation TODO), test035

### Phantoms

#### Phantom: IEC 6 spheres NEMA phantom

An analytical model of the 6 spheres IEC NEMA phantom is provided. It can be used as follows:

```python
import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec

sim = gate.Simulation()
iec_phantom = gate_iec.add_iec_phantom(sim, 'iec_phantom')
activities = [3 * BqmL, 4 * BqmL, 5 * BqmL, 6 * BqmL, 9 * BqmL, 12 * BqmL]
iec_source = gate_iec.add_spheres_sources(sim, 'iec_phantom', 'iec_source', 'all', activities)
iec_bg_source = gate_iec.add_background_source(sim, 'iec_phantom', 'iec_bg_source', 0.1 * BqmL)
```

The rotation should be adapted according to your need. The order of the 6 spheres can be changed with the parameter `sphere_starting_angle` of the `add_iec_phantom` command.

![](figures/iec_6spheres.png)

Example can be found in [test015](https://github.com/OpenGATE/opengate/blob/master/opengate/tests/src/test015_iec_phantom_1.py) (and others).

#### Phantom: cylinder phantom for PET NECR

An analytical model of the simple NECR phantom (cylinder and linear source) is provided. It can be used as follows:


```python
import opengate as gate
import opengate.contrib.phantoms.necr as gate_necr

sim = gate.Simulation()
necr_phantom = gate_necr.add_necr_phantom(sim, 'necr_phantom')
necr_source = gate_necr.add_necr_source(sim, 'necr_phantom')
necr_source.activity = 1000 * Bq
```
Example can be found in [test049](https://github.com/OpenGATE/opengate/blob/master/opengate/tests/src/test049_pet_digit_blurring_v1.py) (and others).


### Radiation therapy linac

**Important Notice**: Please be aware that the models provided within the OpenGate toolkit are based on approximate simulations. Users are strongly encouraged to independently verify these models against empirical data to ensure their applicability and accuracy for specific use cases.

The following models are available:
- Elekta Synergy, without multileaf collimator
- Elekta Versa HD, with Agility multileaf collimator (160 leaves)

```python
import opengate as gate
import opengate.contrib.linacs.elektasynergy as synergy
import opengate.contrib.linacs.elektaversa as versa

sim = gate.Simulation()
linac1 = synergy.add_linac(sim)
linac2 = versa.add_linac(sim)
```


### SPECT imaging systems

**Important Notice**: Please be aware that the models provided within the OpenGate toolkit are based on approximate simulations. Users are strongly encouraged to independently verify these models against empirical data to ensure their applicability and accuracy for specific use cases.

The following models are available:
- GE Discovery 670 SPECT
- Siemens Symbia Intevo Bold SPECT

test028

### PET imaging systems

**Important Notice**: Please be aware that the models provided within the OpenGate toolkit are based on approximate simulations. Users are strongly encouraged to independently verify these models against empirical data to ensure their applicability and accuracy for specific use cases.

The following models are available:
- Philips Vereos Digital PET
- Siemens Biograph Vision PET

test037
