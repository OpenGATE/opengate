/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

/** Authors: Wojciech Krzemień, Mateusz Bała and Kamil Dulski
 *  Emails: wojciech.krzemien@ncbj.gov.pl, mateusz.bala@ncbj.gov.pl and kamil.dulski@gmail.com
 *  Organization: National Centre For Nuclear Research (NCBJ, https://ncbj.gov.pl), Poland
 *  Developed within the IMPET project: https://pet.ncbj.gov.pl/
 *  About class: Geant4 primary event source for positronium annihilation; lazily initializes a GatePositroniumDecayModel from messenger-supplied parameters on the first event and delegates primary vertex generation to the model.
 **/

#ifndef GatePositroniumSource_h
#define GatePositroniumSource_h

#include "GateSingleParticleSource.h"
#include "GateGenericSource.h"
#include <pybind11/stl.h>

#include "GateGammaEmissionModel.h"
#include "GatePositroniumDecayModelParams.h"

namespace py = pybind11;

class GatePositroniumSource : public GateGenericSource {

public:

  GatePositroniumSource();

  ~GatePositroniumSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void GeneratePrimaries(G4Event *event, double time) override;


protected:
  unsigned long fNumberOfGeneratedEvents;

  std::vector<PositroniumDecayKind> ParsePositroniumDecayKind(const std::vector<string> & decayKindsStr);

protected:
  std::unique_ptr<GateGammaEmissionModel> pModel;

};

#endif // GatePositroniumSource_h
