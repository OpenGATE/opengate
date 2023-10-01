## Physics

The managements of the physic in Geant4 is rich and complex, with hundreds of options. OPENGATE proposes a subset of available options.

### Physics list and decay

First, the user needs to select a physics list. A physics list contains a large set of predefined physics options, adapted to different problems. Please refer to the [Geant4 guide](https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html) for a
detailed explanation. The user can select the physics list with the following:

```python
# Assume that sim is a simulation
phys = sim.get_physics_info()
phys.name = 'QGSP_BERT_EMZ'
```

The default physics list is QGSP_BERT_EMV. The Geant4 standard physics list are composed of a first part:

```python
FTFP_BERT
FTFP_BERT_TRV
FTFP_BERT_ATL
FTFP_BERT_HP
FTFQGSP_BERT
FTFP_INCLXX
FTFP_INCLXX_HP
FTF_BIC
LBE
QBBC
QGSP_BERT
QGSP_BERT_HP
QGSP_BIC
QGSP_BIC_HP
QGSP_BIC_AllHP
QGSP_FTFP_BERT
QGSP_INCLXX
QGSP_INCLXX_HP
QGS_BIC
Shielding
ShieldingLEND
ShieldingM
NuBeam
```

And a second part with the electromagnetic interactions:

```python
_EMV
_EMX
_EMY
_EMZ
_LIV
_PEN
__GS
__SS
_EM0
_WVI
__LE
```

The lists can change according to the Geant4 version (this list is for 10.7).

Moreover, additional physics list are available:

```python
G4EmStandardPhysics_option1
G4EmStandardPhysics_option2
G4EmStandardPhysics_option3
G4EmStandardPhysics_option4
G4EmStandardPhysicsGS
G4EmLowEPPhysics
G4EmLivermorePhysics
G4EmLivermorePolarizedPhysics
G4EmPenelopePhysics
G4EmDNAPhysics
G4OpticalPhysics
```

Note that EMV, EMX, EMY, EMZ corresponds to option1, 2, 3, 4 (don't ask us why).

**WARNING** The decay process, if needed, must be added explicitly. This is done with:

```python
sim.enable_decay(True)
# or
sim.physics_manager = True
```

Under the hood, this will add two processed to the Geant4 list of processes, G4DecayPhysics and G4RadioactiveDecayPhysics. Those processes are required in particular if decaying generic ion (such as F18) is used as source. Additional information can be found in the following:

- <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/physicsProcess.html#particle-decay-process>
- <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsReferenceManual/html/decay/decay.html>
- <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html>
- <http://www.lnhb.fr/nuclear-data/nuclear-data-table/>

### Electromagnetic parameters

WARNING : this part is work in progress. DO NOT USE YET.

Electromagnetic parameters are managed by a specific Geant4 object called G4EmParameters. It is available with the following:

```python
phys = sim.get_physics_info()
em = phys.g4_em_parameters
em.SetFluo(True)
em.SetAuger(True)
em.SetAugerCascade(True)
em.SetPixe(True)
em.SetDeexActiveRegion('world', True, True, True)
```

WARNING: it must be set **after** the initialization (after `sim.initialize()` and before `output = sim.start()`).

The complete description is available in this page: <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/physicsProcess.html>

### Managing the cuts and limits

WARNING : this part is work in progress. DO NOT USE YET.

<https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/thresholdVScut.html>

<https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/cutsPerRegion.html>

<https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/userLimits.html>
