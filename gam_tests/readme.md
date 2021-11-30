
Comments about tests (work in progress)


# test 008 and 020

Warning -> 008 need 'random hit' while 020 need 'post hit' ? 


# tests 013 (physics lists)

Test 13 with physics lists. 

Errror for n°3 (different number of track). Don't know why. Not clear how the "decay" is handle in Gate. Maybe related to "G4UAtomicDeexcitation" or "PIXE model" ?

Only since the PR https://github.com/OpenGATE/Gate/pull/440


# test 019 (phsp)

Sometimes, the following error appears: `std::runtime_error: pybind11_object_dealloc()`

# 'multiple' tests

Not clear how to organize 'multiple' tests. For example, t013 use a '_base.py' that create a sim object. Also t019 return a sim object that can be modified before run. But t022 use argv on the command line for t022 with MT. 

