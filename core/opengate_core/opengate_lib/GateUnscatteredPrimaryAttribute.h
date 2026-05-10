/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUnscatteredPrimaryAttribute_h
#define GateUnscatteredPrimaryAttribute_h

#include "GateVAuxiliaryAttribute.h"

class GateUnscatteredPrimaryAttribute : public GateVAuxiliaryAttribute {
public:
  explicit GateUnscatteredPrimaryAttribute(py::dict &user_info);

  void InitializeCpp() override;
  int GetIValue(const G4Step *step) const override;
};

#endif // GateUnscatteredPrimaryAttribute_h
