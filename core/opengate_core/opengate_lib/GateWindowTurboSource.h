#pragma once
#include "GateGenericSource.h"
#include "GateSingleParticleSource.h"
#include <G4Point3D.hh>
#include <G4String.hh>
#include <G4ThreeVector.hh>

/*
author: LiKun (likun@dotuai.com)
source only generated particles that fulfill the following conditions:

Given four points in space, pth1, pth2, pphi1, pphi2
then elevation angle of the particle, theta from the source point, should
between the elevation angles of source point seeing of pth1 and pth2. Also the
azimuthal angle of the particle, phi from the source point, should between the
azimuthal angles of source point seeing pphi1 and pphi2.




*/

class GateWindowTurboSource : public GateGenericSource {
public:
  GateWindowTurboSource(G4String name);
  ~GateWindowTurboSource() = default;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  virtual double PrepareNextTime(double current_simulation_time,
                                 double NumberOfGeneratedEvents) override;

  void Initialize(G4int samplingCount);
  void LoadVoxelizedPhantom(G4String filename);
  void SetPhantomPosition(G4ThreeVector pos);
  void GetWindowVertex(G4ThreeVector &pos1, G4ThreeVector &pos2,
                       G4ThreeVector &pos3, G4ThreeVector &pos4) const;

private:
  void CheckMotherVolumeIsNotRotated() const;
};
