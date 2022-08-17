

-----------------------------------
Test1: Simulation statistics actors
-----------------------------------

50k proton in waterbox

Warning physics
- QGSP_BERT_EMV cut like Gate -> 250 eV min
- add 700 um production cuts

(only needed to compare with Gate)

Compare

.. code:: bash

   cd gate_test1_simulation_stats_actor
   Gate mac/proton.mac
   cat output/stat-world.txt

   ./test1_simulation_stats_actor.py


Timing: around 10 sec (Gate) vs 12 sec (OpenGate)

Without the actor, timing is almost the same (11 sec)



-----------------------------------
Test2: 3D edep actor
-----------------------------------

50k proton in waterbox
QGSP_BERT_EMV cut like Gate -> 250 eV min
(only needed to compare with Gate)

world : 1m
waterbox : 20 cm, position at -15 cm (proton beam at 5cm entrance)

3D dose map

TODO -> warning coord system touchable ?

.. code:: bash

   cd gate_test2_simulation_stats_actor
   Gate mac/proton.mac
   ./analyse.py output

   ./test2_simulation_stats_actor.py


Timing Gate: 50k proton around 10 sec
Timing OpenGate:  50k proton around 31 sec -> 3X slower !

OPENGATE version1: full Python side. Trampoline for SteppingAction
OPENGATE version2:

