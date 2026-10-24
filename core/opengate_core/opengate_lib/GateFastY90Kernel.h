/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateFastY90Kernel_h
#define GateFastY90Kernel_h

#include <array>

// Numerical kernel from GATE 9.4.1 GateSourceFastY90. Energies are in MeV,
// distances in mm and angles in radians, independently of Geant4's unit system.
// The sampling arguments are independent uniform variates in [0, 1).
class GateFastY90Kernel {
public:
  explicit GateFastY90Kernel(double minBremEnergy = 0,
                             double positronProbability = 3.186e-5);

  double GetBremsstrahlungYield() const { return fBremsstrahlungYield; }
  double GetTotalYield() const {
    return fBremsstrahlungYield + fPositronProbability;
  }
  double GetEffectiveMinBremEnergy() const { return fFirstEnergyBin * 0.01; }
  bool IsPositron(double probability) const;
  double SampleBremsstrahlungEnergy(double probability,
                                    double binFraction) const;
  double SamplePositronEnergy(double probability) const;
  double SampleRange(double energy, double probability,
                     double binFraction) const;
  double SampleAngle(double energy, double probability,
                     double binFraction) const;

  static const auto &GetEnergyTable() { return mEnergyTable; }
  static const auto &GetRangeTable() { return mRangeTable; }
  static const auto &GetAngleTable() { return mAngleTable; }
  static const auto &GetPositronEnergyTable() { return mPositronEnergyTable; }

private:
  // Unmodified numerical values from GateSourceFastY90Tables.cc, GATE 9.4.1.
  static const double mEnergyTable[200];
  static const double mRangeTable[100][120];
  static const double mAngleTable[100][180];
  static const double mPositronEnergyTable[738];

  struct ConditionalCDFs {
    ConditionalCDFs();
    std::array<std::array<double, 120>, 100> range;
    std::array<std::array<double, 180>, 100> angle;
  };
  static const ConditionalCDFs &GetConditionalCDFs();

  std::array<double, 200> fEnergyCDF{};
  int fFirstEnergyBin;
  double fBremsstrahlungYield;
  double fPositronProbability;
};

#endif
