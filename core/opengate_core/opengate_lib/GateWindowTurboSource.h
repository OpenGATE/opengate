#pragma once
#include "GateGenericSource.h"
#include "GateSingleParticleSource.h"
#include <G4Colour.hh>
#include <G4Point3D.hh>
#include <G4Polyline.hh>
#include <G4String.hh>
#include <G4ThreeVector.hh>
#include <G4Types.hh>
#include <G4Vector3D.hh>
#include <map>
#include <mutex>

/*
author: LiKun (likun@dotuai.com)
source only generated particles that fulfill the following conditions:

Given four points in space, pth1, pth2, pphi1, pphi2
then elevation angle of the particle, theta from the source point, should
between the elevation angles of source point seeing of pth1 and pth2. Also the
azimuthal angle of the particle, phi from the source point, should between the
azimuthal angles of source point seeing pphi1 and pphi2.




*/

class GateSingleParticleSourceWindowTurbo;

class GateWindowTurboSource : public GateGenericSource {
public:
  GateWindowTurboSource() = default;
  ~GateWindowTurboSource() override = default;

  // void GeneratePrimaries(G4Event *event,
  //                        double current_simulation_time) override;

  virtual void PrepareNextRun() override;

  // void LoadVoxelizedPhantom(G4String filename);
  // void SetPhantomPosition(G4ThreeVector pos);
  void PendingVisualizeWindowWithColourName(G4String colour_name,
                                            G4double width, int run_id);
  void PendingVisualizeWindowWithRGBA(std::vector<G4double> rgba,
                                      G4double width, int run_id);
  void PendingVisualizeWindow(G4Colour colour, G4double width, int run_id);
  void VisualizeOneWindow(G4Colour colour, G4double width, int run_id) const;
  void InitializeUserInfo(py::dict &user_info) override;
  // virtual unsigned long
  // GetExpectedNumberOfEvents(const TimeInterval &time_interval) override;

  virtual double CalcNextTime(double current_simulation_time) override;
  virtual void Visualize() const override;

protected:
  virtual void CreateSPS() override;
  virtual void InitializeDirection(py::dict puser_info) override;

private:
  std::vector<G4double> fA1, fA2, fB1, fB2, fPlaneDistance, fPlanePhi,
      fActRatio, fMaxSolidAngle;
  G4int fCurrentRunId;
  G4double fCurrentActRatio;
  G4double GetValueThisRun(const std::vector<G4double> &vec) const {
    return GetValueThisRun(vec, fCurrentRunId);
  }
  G4double GetValueThisRun(const std::vector<G4double> &vec,
                           G4int run_id) const {
    if (vec.size() == 1)
      return vec[0];
    else
      return vec[run_id];
  }
  void SetValueThisRun(std::vector<G4double> &vec, G4int run_id,
                       G4double value) {
    if (vec.size() == 1)
      vec[0] = value;
    else
      vec[run_id] = value;
  }
  std::vector<G4Colour> visualization_window_color;
  std::vector<G4double> visualization_window_width;
  std::vector<G4int> visualization_window_run_id;

  struct VisWindow {
    VisWindow(const G4Vector3D &pos1, const G4Vector3D &pos2,
              const G4Vector3D &pos3, const G4Vector3D &pos4, G4Colour colour,
              G4double width);
    void operator()(G4VGraphicsScene &, const G4ModelingParameters *);
    G4Polyline fPolyline;
    G4Colour fColour;
    G4double fWidth;
  };
  void GetWindowVertex(G4ThreeVector &pos1, G4ThreeVector &pos2,
                       G4ThreeVector &pos3, G4ThreeVector &pos4,
                       int run_id) const;

  void CallOnceBeforeRun(G4int run_id,
                         GateSingleParticleSourceWindowTurbo *spswt);
  py::dict fUserInfo; // to write back act ratio and max solid angle

  std::once_flag &GetInitializeBeforeRunFlag(G4int run_id);

  std::mutex fInitializeBeforeRunMutex;
  std::map<G4int, std::once_flag> fInitializeBeforeRunFlags = {};
  bool fSkip; // true for act ratio, false for event skipping base on
              // solid angle
  //   void CheckMotherVolumeIsNotRotated() const;
};
