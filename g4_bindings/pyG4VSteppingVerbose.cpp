/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VSteppingVerbose.hh"

void init_G4VSteppingVerbose(py::module &m) {
    py::class_<G4VSteppingVerbose>(m, "G4VSteppingVerbose")

        /*
          protected:
          static G4ThreadLocal G4VSteppingVerbose* fInstance;// pointer to the instance
          static G4ThreadLocal G4int Silent; //flag for verbosity
          static G4ThreadLocal G4int SilentStepInfo; //another flag for verbosity
          public:   // with description
          // static methods to set/get the object's pointer
          static void SetInstance(G4VSteppingVerbose* Instance);
          static G4VSteppingVerbose* GetInstance();
          static G4int GetSilent();
          static void SetSilent(G4int fSilent);
          static G4int GetSilentStepInfo();
          static void SetSilentStepInfo(G4int fSilent);
          // these method are invoked in the SteppingManager
          virtual void NewStep() = 0;
          void CopyState();
          void SetManager(G4SteppingManager* const);
          virtual void AtRestDoItInvoked() = 0;
          virtual void AlongStepDoItAllDone() = 0;
          virtual void PostStepDoItAllDone() = 0;
          virtual void AlongStepDoItOneByOne() = 0;
          virtual void PostStepDoItOneByOne() = 0;
          virtual void StepInfo() = 0;
          virtual void TrackingStarted() = 0;
          virtual void DPSLStarted() = 0;
          virtual void DPSLUserLimit() = 0;
          virtual void DPSLPostStep() = 0;
          virtual void DPSLAlongStep() = 0;
          virtual void VerboseTrack() = 0;
          virtual void VerboseParticleChange() = 0;
          // Member data
          */
        ;

}
