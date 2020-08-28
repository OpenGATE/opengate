/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamSimulationStatisticsActor.h"
#include "GamVActor.h"

/*GamSimulationStatisticsActor::GamSimulationStatisticsActor(std::string name) : G4VPrimitiveScorer(name) {
    std::cout << "GamSimulationStatisticsActor construction " << name << std::endl;
}

GamSimulationStatisticsActor::~GamSimulationStatisticsActor() {
    std::cout << "GamSimulationStatisticsActor destructor " << std::endl;
}

void GamSimulationStatisticsActor::BeforeStart() {

}
*/

void GamSimulationStatisticsActor::BeforeStart() {
    step_count = 0;
}


G4bool GamSimulationStatisticsActor::ProcessHits(G4Step *, G4TouchableHistory *) {
    //std::cout << "GamSimulationStatisticsActor ProcessHits "
    //<< step_count << " " << batch_current << std::endl;
    step_count++; // FIXME not needed
    ProcessBatch(); // not needed FIXME test only
    return true;
}