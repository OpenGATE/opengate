
# User guide


*Why this new GAM project ?*

The GATE project is more than 15 years old. During this time, it evolves a lot, now allowing to perform a wide range of medical physics simulations such as various imaging system (PET, SPECT, Compton Cameras, X-ray, etc) and dosimetry studies (radiotherapy, hadrontherapy, etc). This project led to hundreds of publications. 

GATE fully relies on Geant4 for the Monte Carlo engine and provides 1) easy access to Geant4 functionalities, 2) additional features (e.g. variance reduction techniques) and 3) collaborative development to shared source code, avoiding reinventing the wheel. The user interface is done via so-called `macro` files (`.mac`) that contains Geant4 style macro commands that are convenient compared to direct Geant4 C++ coding. Note that others projects such as Gamos or Topas relies on similar principles.

Since the beginning of GATE, a lot of changes appends in both fields of computer science and medical physics, with, among others, the rise of machine learning and Python language, in particular for data analysis. Also, the Geant4 project is still very active, and is guarantee to be maintained at least for the ten next year (as of 2020). 


*Goal*

The main goal of this project is to provide easier and more flexible way to create Monte Carlo simulation from Geant4 for medical physics. User interface is completely renewed to build simulation no more with macro files but in Python.



Ideally the user will only have to install the Python module via:
```
pip install gam
```
and start create simulation (see user guide). 


interest:
- install, input macro py, redo modern cpp, tests, 
- link itk
- link with pytorch ?

