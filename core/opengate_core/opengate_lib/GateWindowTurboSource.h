#pragma once
#include "GateVSource.h"
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

class GateSourceTurbo : public GateVSource {
public:
  GateSourceTurbo(G4String name);
  ~GateSourceTurbo() { G4cout << "GateSourceTurbo destructs" << G4endl; };

  void GeneratePrimaries(G4Event *event, double current_simulation_time) override;

  
  virtual double PrepareNextTime(double current_simulation_time,
                                 double NumberOfGeneratedEvents);

  // should be reimplemented
  G4double GetNextTime(G4double timeStart) override;
  void SetA1(G4double a) { a1 = a; };
  void SetA2(G4double a) { a2 = a; };
  void SetB1(G4double b) { b1 = b; };
  void SetB2(G4double b) { b2 = b; };
  void SetPlaneDistance(G4double distance) { plane_distance = distance; };
  void SetPlanePhi(G4double phi) { plane_phi = phi; sin_plane_phi = sin(phi); cos_plane_phi = cos(phi); };



  void SetActRatio(G4double actRatio){act_ratio = actRatio;act_ratio_set = true;};
  void SetMaxSolidAngle(G4double maxSolidAngle) { max_solid_angle = maxSolidAngle; max_solid_angle_set = true; };
  void Initialize(G4int samplingCount);
  void LoadVoxelizedPhantom(G4String filename);
  void SetPhantomPosition(G4ThreeVector pos);
  void GetWindowVertex(G4ThreeVector &pos1, G4ThreeVector &pos2, G4ThreeVector &pos3, G4ThreeVector &pos4) const;

private:
  static G4bool random_engine_initialized;
  void SetPhiTheta(const G4ThreeVector &pos) const;
  G4bool CheckPosDirValid(const G4ThreeVector &pos,
                          const G4ThreeVector &dir) const;
  G4double act_ratio = 1;
  G4double max_solid_angle = 0;
  G4bool act_ratio_set;
  G4bool max_solid_angle_set;
  G4double plane_distance{NAN};
  G4double plane_phi{NAN};
  G4double sin_plane_phi{NAN}, cos_plane_phi{NAN};
  G4double a1{NAN}, a2{NAN}, b1{NAN}, b2{NAN};
  void VerifyPhiTheta(G4int number_pos, G4double interval) const;
  // G4ThreeVector mPth1;
  // G4ThreeVector mPth2;
  // G4ThreeVector mPphi1;
  // G4ThreeVector mPphi2;
};