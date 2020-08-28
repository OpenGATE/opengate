/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSimulationStatisticsActor_h
#define GateSimulationStatisticsActor_h

#include "G4VPrimitiveScorer.hh"
#include "GamVActor.h"

class GamSimulationStatisticsActor : public GamVActor {

public:

    GamSimulationStatisticsActor() : GamVActor("SimulationStatistics") {}

    virtual void BeforeStart();

    virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

    int step_count;

};

#endif // GateSimulationStatisticsActor_h
