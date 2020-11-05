import gam
import gam_g4 as g4
import numpy as np
from box import Box


class SingleParticleSource(gam.SourceBase):
    """
    Interface to G4SingleParticleSource
    """

    type_name = 'SingleParticleSource'

    def __init__(self, name):
        gam.SourceBase.__init__(self, name)
        self.g4_sps = None
        self.Bq = gam.g4_units('Bq')
        self.sec = gam.g4_units('s')
        self.MeV = gam.g4_units('MeV')

        # default user param
        self.user_info.particle = 'gamma'
        self.user_info.particle_charge = 0.0
        self.user_info.particle_polarization = [0, 0, 0]
        self.user_info.activity = 1 * self.Bq

        # position
        p = self.user_info.position = Box()
        p.pos_type = 'Point'
        p.shape = 'NULL'
        p.center = [0, 0, 0]
        p.rot_1 = [1, 0, 0]
        p.rot_2 = [0, 1, 0]
        p.half_x = 0
        p.half_y = 0
        p.half_z = 0
        p.radius = 0
        p.radius0 = 0
        p.beam_sigma_in_r = 0
        p.beam_sigma_in_x = 0
        p.beam_sigma_in_y = 0
        p.par_alpha = 0
        p.par_theta = 0
        p.par_phi = 0
        p.confine = False
        p.confine_volume = 'NULL'

        # direction
        d = self.user_info.direction = Box()
        d.ang_dist_type = 'planar'
        d.ang_ref_name = None
        d.ang_ref_axis = None
        d.min_theta = 0
        d.min_phi = 0
        d.max_theta = np.pi
        d.max_phi = 2 * np.pi
        d.beam_sigma_in_ang_r = 0
        d.beam_sigma_in_ang_x = 0
        d.beam_sigma_in_ang_y = 0
        d.user_def_ang_theta = None
        d.user_def_ang_phi = None
        d.focus_point = [0, 0, 0]
        d.momentum_direction = [0, 0, -1]
        d.user_user_ang = False
        d.user_WRT_surface = True

        # energy
        e = self.user_info.energy = Box()
        e.energy_dist_type = 'Mono'
        e.e_min = 0
        e.e_max = 1.e30
        e.mono_energy = 1.0 * self.MeV
        e.alpha = 0
        e.bias_alpha = None
        e.temp = 0
        e.beam_sigma_in_e = 0
        e.e_zero = 0
        e.gradient = 0
        e.intercept = 0
        e.user_energy_histo = None
        e.arb_energy_histo = None
        e.arb_energy_histo_file = None
        e.epn_energy_histo = None
        e.input_energy_spectra = True  # true - energy spectra, false - momentum spectra
        e.input_differential_spectra = True  # true - differential spec, false integral spec
        e.arb_interpolate = None

        # internal data
        self.next_time = -1

    def __str__(self):
        # FIXME
        s = gam.SourceBase.__str__(self)
        s += 'TODO'
        return s

    def __del__(self):
        print('destructor SingleParticleSource')

    def initialize(self, run_timing_intervals):
        gam.SourceBase.initialize(self, run_timing_intervals)

        # FIXME --> check keys in Box pos/ene/ang

        # particle type
        self.g4_sps = g4.G4SingleParticleSource()
        p = self.user_info.particle
        self.particle = self.particle_table.FindParticle(particle_name=p)
        if not self.particle:
            gam.fatal(f'Cannot find the particle {p} for this source: {self.user_info}')
        self.g4_sps.SetParticleDefinition(self.particle)
        self.g4_sps.SetParticleCharge(self.user_info.particle_charge)
        self.g4_sps.SetParticlePolarization(gam.vec_np_as_g4(self.user_info.particle_polarization))
        # self.g4_sps.SetNumberOfParticles(2)
        # self.g4_sps.SetVerbosity(1)

        # position
        p = self.g4_sps.GetPosDist()
        u = self.user_info.position
        pos_types = ['Point', 'Beam', 'Plane', 'Surface', 'Volume']
        if u.pos_type not in pos_types:
            gam.fatal(f'Source Pos type "{u.pos_type}" is unknown. '
                      f'Known types are: {pos_types} ')
        p.SetPosDisType(u.pos_type)
        shape_types = ['Square', 'Circle', 'Annulus', 'Ellipse', 'Rectangle',
                       'Sphere', 'Ellipsoid', 'Cylinder', 'Right', 'NULL']
        if u.shape not in shape_types:
            gam.fatal(f'Source shape type "{u.shape}" is unknown. '
                      f'Known types are: {shape_types} ')
        p.SetPosDisShape(u.shape)
        p.SetCentreCoords(gam.vec_np_as_g4(u.center))
        p.SetPosRot1(gam.vec_np_as_g4(u.rot_1))
        p.SetPosRot2(gam.vec_np_as_g4(u.rot_2))
        p.SetHalfX(u.half_x)
        p.SetHalfY(u.half_y)
        p.SetHalfZ(u.half_z)
        p.SetRadius(u.radius)
        p.SetRadius0(u.radius0)
        p.SetBeamSigmaInX(u.beam_sigma_in_x)
        p.SetBeamSigmaInY(u.beam_sigma_in_y)
        p.SetBeamSigmaInR(u.beam_sigma_in_r)
        p.SetParAlpha(u.par_alpha)
        p.SetParTheta(u.par_theta)
        p.SetParPhi(u.par_phi)
        # FIXME todo later
        # p.ConfineSourceToVolume(u.confine_volume)

        # direction
        d = self.g4_sps.GetAngDist()
        u = self.user_info.direction
        ang_dist_types = ['iso', 'cos', 'user', 'planar', 'beam1d', 'beam2d', 'focused']
        if u.ang_dist_type not in ang_dist_types:
            gam.fatal(f'Source ang_dist type "{u.ang_dist_type}" is unknown. '
                      f'Known types are: {ang_dist_types} ')
        d.SetAngDistType(u.ang_dist_type)
        if u.ang_ref_name and u.ang_ref_axis:
            d.DefineAngRefAxes(u.ang_ref_name, gam.vec_np_as_g4(u.ang_ref_axis))
        d.SetMinTheta(u.min_theta)
        d.SetMinPhi(u.min_phi)
        d.SetMaxTheta(u.max_theta)
        d.SetMaxPhi(u.max_phi)
        d.SetBeamSigmaInAngR(u.beam_sigma_in_ang_r)
        d.SetBeamSigmaInAngX(u.beam_sigma_in_ang_x)
        d.SetBeamSigmaInAngY(u.beam_sigma_in_ang_y)
        if u.user_def_ang_theta:
            d.UserDefAngTheta(gam.vec_np_as_g4(u.user_def_ang_theta))
        if u.user_def_ang_phi:
            d.UserDefAngPhi(gam.vec_np_as_g4(u.user_def_ang_phi))
        d.SetFocusPoint(gam.vec_np_as_g4(u.focus_point))
        d.SetParticleMomentumDirection(gam.vec_np_as_g4(u.momentum_direction))
        d.SetUseUserAngAxis(u.user_user_ang)
        d.SetUserWRTSurface(u.user_WRT_surface)

        # energy
        e = self.g4_sps.GetEneDist()
        u = self.user_info.energy
        energy_dist_types = ['Mono', 'Lin', 'Pow', 'Exp', 'Gauss', 'Brem', 'BBody',
                             'Cdg', 'User', 'Arb', 'Epn']
        if u.energy_dist_type not in energy_dist_types:
            gam.fatal(f'Source energy_dist type "{u.energy_dist_type}" is unknown. '
                      f'Known types are: {energy_dist_types} ')
        e.SetEnergyDisType(u.energy_dist_type)
        e.SetEmin(u.e_min)
        e.SetEmax(u.e_max)
        e.SetMonoEnergy(u.mono_energy)
        e.SetAlpha(u.alpha)
        if u.bias_alpha:
            e.SetBiasAlpha(u.bias_alpha)
        e.SetTemp(u.temp)
        e.SetBeamSigmaInE(u.beam_sigma_in_e)
        e.SetEzero(u.e_zero)
        e.SetGradient(u.gradient)
        e.SetInterCept(u.intercept)
        if u.user_energy_histo:
            e.UserEnergyHisto(u.user_energy_histo)
        if u.arb_energy_histo:
            e.ArbEnergyHisto(u.arb_energy_histo)
        if u.arb_energy_histo_file:
            # FIXME check file exist
            # FIXME arb_interpolate is needed ?
            e.ArbEnergyHistoFile(u.arb_energy_histo_file)
        if u.arb_interpolate:
            e.ArbInterpolate(u.arb_interpolate)
        if u.epn_energy_histo:
            e.EpnEnergyHisto(u.epn_energy_histo)
        e.InputEnergySpectra(u.input_energy_spectra)
        e.InputDifferentialSpectra(u.input_differential_spectra)

        # first time
        t = run_timing_intervals[0][0]
        self.next_time = t + -np.log(g4.G4UniformRand()) * (1.0 / self.user_info.activity)

    def get_estimated_number_of_events(self, run_timing_interval):
        duration = run_timing_interval[1] - run_timing_interval[0]
        n = self.user_info.activity / self.Bq * duration / self.sec
        return n

    def source_is_terminated(self, sim_time):
        # Check if the source is terminated with the future time
        # (this prevent to have an empty Event)
        if self.next_time > self.user_info.end_time:
            return True
        return False

    def get_next_event_info(self, current_time):
        # if the next time is in the future, we are still return the current next time
        if current_time < self.next_time:
            return self.next_time, self.shot_event_count + 1
        # if this is not the case, we plan a new 'next time'
        self.next_time = current_time + -np.log(g4.G4UniformRand()) * (1.0 / self.user_info.activity)
        return self.next_time, self.shot_event_count + 1

    def generate_primaries(self, event, sim_time):
        self.g4_sps.SetParticleTime(sim_time)
        self.g4_sps.GeneratePrimaryVertex(event)
        self.shot_event_count += 1
