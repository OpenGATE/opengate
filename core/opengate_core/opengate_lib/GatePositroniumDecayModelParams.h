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
 *  About class: Data structure holding all per-component parameters for the positronium decay model: fractions, lifetimes, decay kinds (2γ/3γ), positron-electron interaction types, electron capture probabilities, prompt gamma parameters, and positron range settings.
 **/

#ifndef GatePositroniumDecayModelParams_h
#define GatePositroniumDecayModelParams_h

#include <vector>

enum PositroniumDecayKind {k2Gamma, k3Gamma};

enum PositronElectronInteraction {kParaPs, kDirect, kOrthoPs};

struct PositroniumDecayModelParams
{
  std::vector<double> fFractions;
  std::vector<double> fLifetimes;
  std::vector<double> fPromptGammaProbabilities;
  std::vector<double> fPromptGammaEnergy;
  std::vector<PositroniumDecayKind> fDecayKind;
  std::vector<PositronElectronInteraction> fPositronInteractions;
  std::vector<double> fMeanPositronRange;
  std::vector<double> fElectronCaptureProbabilities;
};

#endif
