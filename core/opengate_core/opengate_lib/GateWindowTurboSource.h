#pragma once
#include "GateGenericSource.h"
#include "GateSingleParticleSource.h"
#include <G4Color.hh>
#include <G4Point3D.hh>
#include <G4Polyline.hh>
#include <G4String.hh>
#include <G4ThreeVector.hh>
#include <G4Types.hh>
#include <G4Vector3D.hh>
#include <memory>
#include <mutex>
#include <vector>

/*
author: LiKun (likun@dotuai.com/tontyoutoure@gmail.com)
source only generated particles that fulfill the following conditions:

Given four points in space, pth1, pth2, pphi1, pphi2
then elevation angle of the particle, theta from the source point, should
between the elevation angles of source point seeing of pth1 and pth2. Also the
azimuthal angle of the particle, phi from the source point, should between the
azimuthal angles of source point seeing pphi1 and pphi2.

*/

class GateSingleParticleSourceWindowTurbo;

struct GateWindowTurboSharedCache {
  std::mutex fMutex;
  std::vector<G4double> fActRatio;
  std::vector<G4double> fMaxSolidAngle;
  std::vector<G4double> fInitDuration;
};

class GateWindowTurboSource : public GateGenericSource {
public:
  GateWindowTurboSource() = default;
  ~GateWindowTurboSource() override = default;

  virtual void PrepareNextRun() override;
  void SetSharedCache(std::shared_ptr<GateWindowTurboSharedCache> cache);

  void VisualizeOneWindow(G4Color color, G4double width, int run_id) const;
  void InitializeUserInfo(py::dict &user_info) override;
  virtual double CalcNextTime(double current_simulation_time) override;
  virtual void Visualize() const override;

protected:
  virtual void CreateSPS() override;
  virtual void InitializeDirection(py::dict puser_info) override;
  virtual void InitializeVisualization(py::dict user_info) override;

private:
  std::vector<G4double> fA1, fA2, fB1, fB2, fPlaneDistance, fPlanePhi;
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
  void SetValueThisRun(std::vector<G4double> &vec, G4double value) {
    if (vec.size() == 1)
      vec[0] = value;
    else
      vec[fCurrentRunId] = value;
  }
  std::vector<G4Color> visualization_window_color;
  std::vector<G4double> visualization_window_width;
  std::vector<G4int> visualization_window_run_id;

  struct VisWindow {
    VisWindow(const G4Vector3D &pos1, const G4Vector3D &pos2,
              const G4Vector3D &pos3, const G4Vector3D &pos4, G4Color color,
              G4double width);
    void operator()(G4VGraphicsScene &, const G4ModelingParameters *);
    G4Polyline fPolyline;
    G4Color fColor;
    G4double fWidth;
  };
  void GetWindowVertex(G4ThreeVector &pos1, G4ThreeVector &pos2,
                       G4ThreeVector &pos3, G4ThreeVector &pos4,
                       int run_id) const;

  void PrepareSharedBeforeRun();
  void InitializeSharedCache(py::dict &user_info);
  void WriteBackUserInfo();
  py::dict fUserInfo; // to write back act ratio and max solid angle

  std::shared_ptr<GateWindowTurboSharedCache> fSharedCache;
  bool fSkip; // true for act ratio, false for event skipping base on
              // solid angle
};
