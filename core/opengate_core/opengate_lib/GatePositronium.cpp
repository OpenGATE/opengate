/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4DecayProducts.hh"
#include "G4ParticleTable.hh"
#include "G4DecayTable.hh"
#include "G4ParticleDefinition.hh"

#include "GatePositronium.h"

GatePositronium::GatePositronium(const G4String& name, G4double life_time): fName(name), fLifeTime(life_time)
{
  //pDecayChannel = new GatePositroniumDecayChannel("pPs", 0.1);
  pDecayChannel = new GatePositroniumDecayChannel("gamma", 0.1);
  //G4ParticleTable::GetParticleTable()->DumpTable();
  //G4ParticleDefinition *positronium_def = G4ParticleTable::GetParticleTable()->FindParticle(name);
  //if (positronium_def==nullptr) {
    //std::cout << "no particle found in GetParticleTable" << std::endl;
  //} 
  //G4DecayTable *positronium_decay_table = positronium_def->GetDecayTable();
  //std::cout << "in ctr GatePositronium 3" << std::endl;
  //pDecayChannel = static_cast<GatePositroniumDecayChannel*>(positronium_decay_table->GetDecayChannel(0));
  ////std::cout << "in ctr GatePositronium 4" << std::endl;
}

G4double GatePositronium::GetLifeTime() const { return fLifeTime; }

const G4String& GatePositronium::GetName() const { return fName; }

G4int GatePositronium::GetAnnihilationGammasNumber() const { return pDecayChannel->GetNumberOfDaughters(); }

G4DecayProducts* GatePositronium::GetDecayProducts() const { return pDecayChannel->DecayIt(); }
