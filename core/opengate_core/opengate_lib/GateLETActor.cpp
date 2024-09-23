/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateLETActor.h"
#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "G4Deuteron.hh"
#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4MaterialTable.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4Positron.hh"
#include "G4Proton.hh"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetLETPixelMutex = G4MUTEX_INITIALIZER;

G4Mutex SetLETNbEventMutex = G4MUTEX_INITIALIZER;

GateLETActor::GateLETActor(py::dict &user_info) : GateWeightedEdepActor(user_info) {

}

void GateLETActor::InitializeUserInput(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateWeightedEdepActor::InitializeUserInput(user_info);

  fAveragingMethod = DictGetStr(user_info, "averaging_method");
  
}


void GateLETActor::AddValuesToImages(G4Step *step, ImageType::IndexType index){

    // get edep in MeV (take weight into account)
    auto w = step->GetTrack()->GetWeight();
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
    double dedx_cut = DBL_MAX;

    auto *current_material = step->GetPreStepPoint()->GetMaterial();
    auto density = current_material->GetDensity() / CLHEP::g * CLHEP::cm3;
    const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();

    auto energy1 = step->GetPreStepPoint()->GetKineticEnergy() / CLHEP::MeV;
    auto energy2 = step->GetPostStepPoint()->GetKineticEnergy() / CLHEP::MeV;
    auto energy = (energy1 + energy2) / 2;
    // Accounting for particles with dedx=0; i.e. gamma and neutrons
    // For gamma we consider the dedx of electrons instead - testing
    // with 1.3 MeV photon beam or 150 MeV protons or 1500 MeV carbon ion
    // beam showed that the error induced is 0 		when comparing
    // dose and dosetowater in the material G4_WATER For neutrons the dose
    // is neglected - testing with 1.3 MeV photon beam or 150 MeV protons or
    // 1500 MeV carbon ion beam showed that the error induced is < 0.01%
    //		when comparing dose and dosetowater in the material
    // G4_WATER (we are systematically missing a little bit of dose of
    // course with this solution)

    if (p == G4Gamma::Gamma()) {
      p = G4Electron::Electron();
    }
    auto &l = fThreadLocalData.Get();
    auto dedx_currstep =
        l.emcalc.ComputeElectronicDEDX(energy, p, current_material, dedx_cut) /
        CLHEP::MeV * CLHEP::mm;

    if (fScoreInOtherMaterial) {
      auto dedx_other_material = l.emcalc.ComputeElectronicDEDX(
                                     energy, p, l.materialToScoreIn, dedx_cut) /
                                 CLHEP::MeV * CLHEP::mm;

      // Do we not need to consider the density ratio as well?
      //      auto density_other_material = l.materialToScoreIn->GetDensity() /
      //      CLHEP::g * CLHEP::cm3; auto density_current_material =
      //      current_material->GetDensity() / CLHEP::g * CLHEP::cm3;

      auto SPR_otherMaterial = dedx_other_material / dedx_currstep;
      if (!std::isnan(SPR_otherMaterial)) {
        edep *= SPR_otherMaterial;
        dedx_currstep *= SPR_otherMaterial;
      }
    }

    double scor_val_num = 0.;
    double scor_val_den = 0.;

    if (fAveragingMethod == "dose_average") {
      scor_val_num = edep * dedx_currstep / CLHEP::MeV / CLHEP::MeV * CLHEP::mm;
      scor_val_den = edep / CLHEP::MeV;
    } else if (fAveragingMethod == "track_average") {
      auto steplength = step->GetStepLength() / CLHEP::mm;
      scor_val_num = steplength * dedx_currstep * w / CLHEP::MeV;
      scor_val_den = steplength * w / CLHEP::mm;
    }
    ImageAddValue<ImageType>(cpp_numerator_image, index, scor_val_num);
    ImageAddValue<ImageType>(cpp_denominator_image, index, scor_val_den);
    //}


}

