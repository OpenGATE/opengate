/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateInfo.h"
#include "G4Version.hh"
#include <itkVersion.h>

#ifdef G4MULTITHREADED

#include "G4MTRunManager.hh"

#else
#include "G4RunManager.hh"
#endif

bool GateInfo::get_G4MULTITHREADED() {
#ifdef G4MULTITHREADED
  return true;
#else
  return false;
#endif
}

std::string GateInfo::get_G4Version() { return G4Version; }

std::string GateInfo::get_G4Date() { return G4Date; }

std::string GateInfo::get_ITKVersion() { return itk::Version::GetITKVersion(); }

bool GateInfo::get_G4GDML() {
#ifdef USE_GDML
  return true;
#else
  return false;
#endif
}

#include "G4LinInterpolator.hh"
#include "G4PixeCrossSectionHandler.hh"
#include "G4PixeShellDataSet.hh"

void GateInfo::test() {
  DDD("test");
  auto *h = new G4PixeCrossSectionHandler();
  h->PrintData();
  DDD("ok");
  auto *algo = new G4LinInterpolator();
  auto *dataSet = new G4PixeShellDataSet(89, algo);
  DDD("new ok");
  dataSet->LoadData("alpha");
  DDD("load ok");
  dataSet->PrintData();
  DDD(dataSet->NumberOfComponents());

  auto energies = dataSet->GetEnergies(0);
  for (auto ene : energies) {
    DDD(ene / CLHEP::keV);
  }

  energies = dataSet->GetEnergies(1);
  for (auto ene : energies) {
    DDD(ene / CLHEP::keV);
  }

  DDD("end");
}
