/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateRBEActor.h"
#include "G4LinInterpolation.hh"
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

#include <cmath>

GateRBEActor::GateRBEActor(py::dict &user_info) : GateWeightedEdepActor(user_info) {
  
}

void GateRBEActor::InitializeUserInput(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateWeightedEdepActor::InitializeUserInput(user_info);

  fRBEmodel = DictGetStr(user_info, "rbe_model");
  fAlpha0 = DictGetDouble(user_info, "alpha_0");
  fBeta0 = DictGetDouble(user_info, "beta_0");
  fAreaNucl =  DictGetDouble(user_info, "A_nucleus");
  fDcut =  DictGetDouble(user_info, "D_cut");
  fSmax =  DictGetDouble(user_info, "s_max");
  table = new std::vector<G4DataVector *>;
  CreateLookupTable(user_info);
  
}

void GateRBEActor::InitializeCpp(){
    GateWeightedEdepActor::InitializeCpp();
    cpp_dose_image = ImageType::New();
    if (fRBEmodel == "lemIlda"){
        cpp_numerator_beta_image = ImageType::New();
    }
}

void GateRBEActor::BeginOfRunActionMasterThread(int run_id) {
  GateWeightedEdepActor::BeginOfRunActionMasterThread(run_id);
  AttachImageToVolume<ImageType>(cpp_dose_image, fPhysicalVolumeName,
                                     fInitialTranslation);
  if (fRBEmodel == "lemIlda"){
      // Important ! The volume may have moved, so we re-attach each run
      AttachImageToVolume<ImageType>(cpp_numerator_beta_image, fPhysicalVolumeName,
                                         fInitialTranslation);
  }
}

void GateRBEActor::AddValuesToImages(G4Step *step, ImageType::IndexType index){

    auto event_id =
    G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    // std::cout<<"Event ID: " << event_id << std::endl;

    // get edep in MeV (take weight into account)
    auto w = step->GetTrack()->GetWeight();
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;

    //  other material
    const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();

    auto energy1 = step->GetPreStepPoint()->GetKineticEnergy() / CLHEP::MeV;
    auto energy2 = step->GetPostStepPoint()->GetKineticEnergy() / CLHEP::MeV;
    auto energy = (energy1 + energy2) / 2;

    if (p == G4Gamma::Gamma())
      p = G4Electron::Electron();
    /*auto dedx_currstep =
        emcalc->ComputeElectronicDEDX(energy, p, current_material, dedx_cut) /
        CLHEP::MeV * CLHEP::mm;*/
    auto charge = int(p->GetAtomicNumber());
    auto mass = p->GetAtomicMass();
    auto table_value = GetValue(charge, energy / mass); // energy has unit?

//     std::cout<< "energy:" << energy << ", mass: " << mass << std::endl;
//     std::cout << "Charge: " << charge << ", energy/mass: " << energy/mass << std::endl; 
//     std::cout <<"z*_1D: " << table_value << ", alpha_step: " << alpha_currstep<< std::endl;

    // auto steplength = step->GetStepLength() / CLHEP::mm;
    double scor_val_num = 0.;
    double scor_val_den = 0.;
    
    // calc dose deposited at current step
    auto *current_material = step->GetPreStepPoint()->GetMaterial();
    auto density = current_material->GetDensity();
    auto d_step = edep / (density*fVoxelVolume) / CLHEP::gray;
    
    if (fRBEmodel == "mkm"){
        auto alpha_currstep = fAlpha0 + fBeta0 * table_value;
        scor_val_num = edep * alpha_currstep / CLHEP::mm;
        scor_val_den = edep / CLHEP::mm;
        ImageAddValue<ImageType>(cpp_numerator_image, index, scor_val_num);
        ImageAddValue<ImageType>(cpp_denominator_image, index, scor_val_den);
    }
    
    if (fRBEmodel == "lemIlda"){
        double dedx_cut = DBL_MAX;
        double scor_val_num_beta = 0.;
        auto &l = fThreadLocalData.Get();
        auto dedx_currstep =
            l.emcalc.ComputeElectronicDEDX(energy, p, current_material, dedx_cut) /
            CLHEP::MeV * CLHEP::mm;
        //TODO: implement alpha and beta calculations        
    
    }
    
    if (fRBEmodel == "lemI"){
        // FIXME: no MT supported yet!!
        // here we need the accumulated dose in the voxel
        // get dose accumulated up to this event
        auto d_acc = cpp_dose_image->GetPixel(index);
        double NlethStep;
        // check Dcut condition
        if ((d_acc + d_step) < fDcut){
            NlethStep = d_step*table_value + (fSmax - table_value)*(d_acc + d_step)/fDcut;      
        }
        else{
            NlethStep = fSmax;
        }
        scor_val_num = exp(-NlethStep);
        ImageAddValue<ImageType>(cpp_numerator_image, index, scor_val_num);
    }
    
    ImageAddValue<ImageType>(cpp_dose_image, index, d_step);

    // std::cout << "Index: " << index << "is written in images. " << std::endl;

  } // else : outside the image


void GateRBEActor::CreateLookupTable(py::dict &user_info) {
  // get lookup table
  std::vector<std::vector<double>> lookupTab =
      DictGetVecofVecDouble(user_info, "lookup_table");
  // energies = VectorToG4DataVector(lookupTab[0]);

  for (int i = 1; i < lookupTab.size(); i++) {
    table->push_back(VectorToG4DataVector(lookupTab[i]));
  }
}

double GateRBEActor::GetValue(int Z, float energy) {
  // std::cout << "GetValue: Z: " << Z << ", energy[MeV/u]: " << energy <<
  // std::endl;
  // initalize value
  G4double y = 0;
  // get table values for the given Z
  //   if (Z > 6 || Z < 1 ){
  // 	  return 0;}
  //   G4DataVector *data = (*table)[Z - 1];
  G4DataVector *Z_vec = new G4DataVector();
  Z_vec->insertAt(0, Z);
  int bin_table = -1;
  G4DataVector *energies;
  G4DataVector *data;
  
  for (int i = 0; i < table->size(); i++) {
    if (*(*table)[i] == *Z_vec) {
      bin_table = i;
      energies = (*table)[i + 1];
      data = (*table)[i + 2];
    }
  }
  //std::cout<<"bin_table: "<<bin_table<<std::endl;
  if (bin_table == -1) {
    return 0;
  }
  
  // find the index of the lower bound energy to the given energy
  size_t bin = FindLowerBound(energy, energies);
  // std::cout << "interpolation bin: " << bin << std::endl;
  G4LinInterpolation linearAlgo;
  // get table value for the given energy
  y = linearAlgo.Calculate(energy, bin, *energies, *data);
  // std::cout<<"interpolation output:" << y << std::endl;

  return y;
}

size_t GateRBEActor::FindLowerBound(G4double x, G4DataVector *values) const {
  size_t lowerBound = 0;
  size_t upperBound(values->size() - 1);
  if (x < (*values)[0]) {
    return 0;
  }
  if (x > (*values).back()) {
    return values->size() - 1;
  }
  while (lowerBound <= upperBound) {
    size_t midBin((lowerBound + upperBound) / 2);
    // std::cout<<"upper: "<<upperBound<<" lower: "<<lowerBound<<std::endl;
    // std::cout<<(*values)[midBin]<<std::endl;
    if (x < (*values)[midBin])
      upperBound = midBin - 1;
    else
      lowerBound = midBin + 1;
  }
  return upperBound;
}

//void GateRBEActor::EndSimulationAction() {}
