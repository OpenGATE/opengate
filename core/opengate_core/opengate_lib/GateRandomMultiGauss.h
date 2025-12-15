/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateRandomMultiGauss_h
#define GateRandomMultiGauss_h

#include <vector>

using namespace std;

class GateRandomMultiGauss {

public:
  GateRandomMultiGauss(const vector<double> &muVin,
                       const vector<double> &sigmaMin);

  ~GateRandomMultiGauss();

  vector<double> Fire();

protected:
  vector<double> muV;
  vector<double> sigmaM;
  double a, b, c, d;
  double eigVal1, eigVal2;
  vector<double> eigVec1;
  vector<double> eigVec2;

  void eigenVal();
  vector<double> eigenVector(double eigenValue) const;
  void eigenVectors();
  vector<double> SigmaIndex(double x1_o, double x2_o) const;
};

#endif
