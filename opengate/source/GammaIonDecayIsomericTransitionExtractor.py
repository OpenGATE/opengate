import opengate as gate
import opengate_core as g4
from box import Box
import re
import math


class GammaIonDecayIsomericTransitionExtractor:
    """

    For a given ion, extract all possible gamma emission, with corresponding intensity

    1. Create a 'fake' gate simulation because G4 engine must be initialized. This is done
    in a separate process. The function "_get_all_gamma_emissions" is used.

    2. From the IonTable all the Decay Channels are extracted
        -> function '_get_all_decay_channels'

    3. For one decay channel, we look all possible excitation levels
        This is read in the G4 data file G4LEVELGAMMADATA of the corresponding ion
        -> _get_gammas_for_one_channel
        -> _get_gammas_for_one_level

    """

    def __init__(self, z, a, verbose=False):
        self.z = z
        self.a = a
        self.channels = None
        self.gammas = []
        self.verbose = verbose

    def extract(self):
        # we need to create and run a simulation
        # in order to access all G4 constructed objects
        sim = gate.Simulation()
        sim.user_info.verbose_level = gate.NONE
        # decay is enabled in this phys list
        sim.get_physics_user_info().physics_list_name = "QGSP_BIC_HP"
        sim.apply_g4_command("/particle/nuclideTable/min_halflife 0 ns")
        s = sim.add_source("GenericSource", "fake")
        s.n = 1  # will not be used because init_only is True, but avoid warning
        # prepare to run (in a separate process)
        se = gate.SimulationEngine(sim, start_new_process=True)
        se.init_only = True
        se.user_fct_after_init = self._get_all_gamma_emissions
        # init
        self.gammas = []
        output = se.start()
        # store results in the current process
        self.gammas = output.gammas

    def _get_all_gamma_emissions(self, simulation_engine, output):
        # get all decay channels (first level only)
        self.channels = self._get_all_decay_channels()

        # find gammas for all channels
        for ch in self.channels:
            self._get_gammas_for_one_channel(ch)

        # merge similar lines
        v = self.verbose
        keV = gate.g4_units("keV")
        gamma_final = {}
        v and print()
        v and print(f"Merge")
        for g in self.gammas:
            e = g.transition_energy
            if e in gamma_final:
                v and print(
                    f"Add intensities for {e / keV} keV : {gamma_final[e].final_intensity} + {g.final_intensity} for  {g}"
                )
                gamma_final[e].final_intensity += g.final_intensity
            else:
                gamma_final[e] = g
        self.gammas = []
        for g in gamma_final.values():
            self.gammas.append(g)
        self.gammas = sorted(self.gammas, key=lambda x: x["transition_energy"])

        # print
        if v:
            for g in self.gammas:
                print(
                    f"{g['transition_energy'] / keV} keV   = {g['final_intensity'] * 100}%"
                )

        # store output
        output.gammas = self.gammas

    def _get_all_decay_channels(self):
        # get ion
        ion_table = g4.G4IonTable.GetIonTable()
        ion = ion_table.GetIon(self.z, self.a, 0)

        # get the decay table
        process_table = g4.G4ProcessTable.GetProcessTable()
        decay_process = process_table.FindRadioactiveDecay()
        decay_table = decay_process.GetDecayTable(ion)

        # get all decay channels (first level)
        channels = []
        keV = gate.g4_units("keV")
        for i in range(decay_table.entries()):
            channel = decay_table.GetDecayChannel(i)
            for j in range(channel.GetNumberOfDaughters()):
                d = channel.GetDaughter(j)
                n = d.GetParticleName()
                t = d.GetParticleType()
                if n == "alpha" or t != "nucleus":
                    continue
                ch = Box()
                ch.name = str(d.GetParticleName())
                ch.ion = d
                ch.z = d.GetAtomicNumber()
                ch.a = d.GetAtomicMass()
                ch.br = channel.GetBR()
                ch.energy_label = None
                ch.excitation_energy = d.GetExcitationEnergy()
                ch.excitation_energy_label = 0
                # get the energy label
                # This is tricky : in order to retrieve the correct channel
                # we extract the Energy in the name such as Hf177[321.316] -> 321.316
                # then it will be compared to the excitation energy
                result = re.search(r"(.*)\[(.*)\]", ch.name)
                if result:
                    ch.excitation_energy_label = float(result.groups()[1]) * keV
                channels.append(ch)
        return channels

    def _get_gammas_for_one_channel(self, channel):
        v = self.verbose
        if channel.excitation_energy == 0:
            return
        # read database file
        v and print()
        v and print(f"Channel {channel}")
        levels = gate.isomeric_transition_read_g4_data(channel.z, channel.a)

        # from the name extract the level
        for level in levels.values():
            # We compare label with E as float number
            if math.isclose(
                level.excitation_energy, channel.excitation_energy_label, rel_tol=1e-9
            ):
                v and print()
                v and print(f"Analysing channel {channel.name}")
                g = self._get_gammas_for_one_level(levels, level, br=channel.br)
                self.gammas = self.gammas + g
                break
            # earlier termination (no need to check other level when too large)
            if level.excitation_energy > channel.excitation_energy_label * 1.1:
                break
        # it can happen that no corresponding level is found
        # for example for z87.a221 Fr221[712.000]
        # 712 keV leads to no gamma

    def _get_gammas_for_one_level(self, levels, level, br, p=1, tab=""):
        g_level = []
        g_level_final = []
        total_p = 0
        if br == 0:
            return g_level_final

        # compute Ig = gamma intensity for all daughters and total Ig
        for d in level.daugthers.values():
            lev = self._level_daughter_info(d)
            if lev is not None:
                g_level.append(lev)
                total_p += lev.transition_intensity * (lev.alpha + 1)

        if total_p == 0:
            return g_level_final

        # compute the relative intensity
        # consider also the branching ratio and 'p' which is the probability in case
        # of fallback from another level
        v = self.verbose
        keV = gate.g4_units("keV")
        v and print(
            f"{tab}Level = {level.order_level} E={level.excitation_energy / keV} keV  "
            f"nb_levels = {level.n_gammas}  branching_ratio={br:.5f}    current_proba={p:.5f}"
        )
        tab = f"{tab}    "
        for lev in g_level:
            lev.transition_intensity = (
                (lev.alpha + 1) * lev.transition_intensity / total_p
            )
            # This is the key computation of the probability
            # P = BR x Pg x It x current_p
            # BR = Branching ratio
            # Pg = gamma emission probability
            # It = total transition probability =  Ic + Ig
            # Ig = transition_intensity
            # alpha = Ic/Ig
            lev.final_intensity = (
                lev.prob_gamma_emission * lev.transition_intensity * br * p
            )
            v and print(
                f"{tab}P{level.order_level}->{lev.daughter_order}     E={lev.transition_energy / keV} keV "
                f"br={br:.5f}  trans_int = {lev.transition_intensity:.5f} {lev.prob_gamma_emission:.5f}"
                f"   ->  final intensity = {100 * lev.final_intensity:.5f}% "
            )
            g_level_final.append(lev)
            p2 = lev.transition_intensity
            if lev.daughter_order != 0:
                s = str(lev.daughter_order)
                if s in levels:
                    l2 = levels[s]
                    g = self._get_gammas_for_one_level(levels, l2, br, p2, tab)
                    g_level_final = g_level_final + g
                else:
                    gate.warning(f"Unknown level {s}, ignoring ...")
                    continue

        return g_level_final

    def _level_daughter_info(self, d):
        g = Box()
        g.daughter_order = d.daughter_order
        g.transition_energy = d.transition_energy
        g.transition_intensity = d.intensity
        g.alpha = d.alpha
        g.prob_gamma_emission = 1 / (1 + g.alpha)
        return g
