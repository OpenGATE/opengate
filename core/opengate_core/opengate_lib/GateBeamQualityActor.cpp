/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateBeamQualityActor.h"
#include "G4LinInterpolation.hh"
#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include <itkImageRegionIterator.h>

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

G4Mutex SetRBEPixelMutex = G4MUTEX_INITIALIZER;

GateBeamQualityActor::GateBeamQualityActor(py::dict &user_info)
    : GateWeightedEdepActor(user_info) {}

void GateBeamQualityActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateWeightedEdepActor::InitializeUserInfo(user_info);

  fRBEmodel = DictGetStr(user_info, "model");
  if (fRBEmodel == "mMKM") {
    fAlpha0 = DictGetDouble(user_info, "alpha_0");
    fBetaRef = DictGetDouble(user_info, "beta_ref");
  }
  if (fRBEmodel == "LEM1lda") {
    fAreaNucl = DictGetDouble(user_info, "A_nucleus") * CLHEP::um * CLHEP::um;
    fDcut = DictGetDouble(user_info, "D_cut");
    fSmax = DictGetDouble(user_info, "s_max");
    multipleScoring = true;
  }
  ZMinTable = DictGetInt(user_info, "z_min_table");
  ZMaxTable = DictGetInt(user_info, "z_max_table");
  table = new std::vector<G4DataVector *>;
  CreateLookupTable(user_info);
}

double GateBeamQualityActor::ScoringQuantityFn(G4Step *step,
                                               double *secondQuantity) {
  auto *current_material = step->GetPreStepPoint()->GetMaterial();
  auto density = current_material->GetDensity() / CLHEP::g * CLHEP::cm3;
  const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();
  auto &l = fThreadLocalData.Get();
  auto dedx_currstep = l.dedx_currstep;

  // if (p == G4Gamma::Gamma()) {
  // p = G4Electron::Electron();
  //}

  auto charge = int(p->GetAtomicNumber());
  // auto mass = p->GetAtomicMass();
  auto table_value = GetValue(charge, l.energy_mean);

  if (fRBEmodel == "LEM1lda") {
    double dedx_cut = DBL_MAX;
    auto alpha_z = table_value;
    auto beta_z = (fSmax - alpha_z) / (2 * fDcut);

    double local_d = 0.;
    if (dedx_currstep) {
      local_d = dedx_currstep / (fAreaNucl * density) / CLHEP::gray;
      // FIXME: density of local material here?
    }
    auto alpha_currstep = 0.;
    auto sqrt_beta_currstep = 0.;
    if (local_d) {
      alpha_currstep = (1 - exp(-alpha_z * local_d)) / local_d;
    }
    if (alpha_z) {
      sqrt_beta_currstep = (alpha_currstep / alpha_z) * std::sqrt(beta_z);
    }
    *secondQuantity =
        sqrt_beta_currstep; // dereference pointer to assign value to variable

    return alpha_currstep;

  } else {
    return table_value; // for RE and mMKM the scoring quantity is just the
                        // table value
  }
}

// void GateBeamQualityActor::EndOfRunActionMasterThread() {
// std::cout << "RBE model: " << fRBEmodel << std::endl;

// std::cout << "Alpha: " << fAlpha0 << std::endl;

// std::cout << "Beta ref: " << fBetaRef << std::endl;
// if (fRBEmodel == "mMKM") {
//// postprocess numerator image to get alpha
// itk::ImageRegionIterator<Image3DType> iterator3D(
// cpp_numerator_image, cpp_numerator_image->GetLargestPossibleRegion());
// for (iterator3D.GoToBegin(); !iterator3D.IsAtEnd(); ++iterator3D) {

// Image3DType::IndexType index_f = iterator3D.GetIndex();
// Image3DType::PixelType Q = cpp_numerator_image->GetPixel(index_f);
// Image3DType::PixelType Edep = cpp_denominator_image->GetPixel(index_f);

// std::cout << "Pixel val before:" <<
// cpp_numerator_image->GetPixel(index_f)/Edep << std::endl;
// cpp_numerator_image->SetPixel(index_f,
//(fBetaRef * Q + fAlpha0 * Edep) );
// std::cout << "Pixel val after:" << cpp_numerator_image->GetPixel(index_f) <<
// std::endl;
//}
//}
//}

void GateBeamQualityActor::CreateLookupTable(py::dict &user_info) {
  // get lookup table
  std::vector<std::vector<double>> lookupTab =
      DictGetVecofVecDouble(user_info, "lookup_table");
  // energies = VectorToG4DataVector(lookupTab[0]);

  for (int i = 0; i < lookupTab.size(); i++) {
    table->push_back(VectorToG4DataVector(lookupTab[i]));
  }
}

double GateBeamQualityActor::GetValue(int Z, float energy) {
  // std::cout << "GetValue: Z: " << Z << ", energy[MeV]: " << energy <<
  // std::endl;
  // initalize value
  G4double y = 0;
  // std::cout<< "Particle: "<< Z << std::endl;
  // std::cout<< "Energy: "<< energy << std::endl;
  // std::cout<< "Zmin: "<< ZMinTable << "      " << "Zmax: "<< ZMaxTable <<
  // std::endl;
  if (Z > ZMaxTable) {
    Z = ZMaxTable;
  }
  if ((Z >= ZMinTable) && (Z <= ZMaxTable)) {
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
    // find the index of the lower bound energy to the given energy
    size_t bin = FindLowerBound(energy, energies);
    // std::cout << "interpolation bin: " << bin << std::endl;
    G4LinInterpolation linearAlgo;
    // get table value for the given energy
    y = linearAlgo.Calculate(energy, bin, *energies, *data);
    // std::cout<<"interpolation output:" << y << std::endl;
    // std::cout<<"        "<<std::endl;
    delete Z_vec;
    Z_vec = nullptr;
    return y;
  } else {
    return 0;
  }
}

size_t GateBeamQualityActor::FindLowerBound(G4double x,
                                            G4DataVector *values) const {
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

// void GateBeamQualityActor::EndSimulationAction() {}
