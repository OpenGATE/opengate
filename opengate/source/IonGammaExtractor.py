import opengate as gate
import radioactivedecay as rd
import opengate_core as g4
from box import Box
import re


class IonGammaExtractor:
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
        # decay must be enabled
        sim.get_physics_user_info().enable_decay = True
        # fake source, only one particle
        s = sim.add_source("GenericSource", "s")
        s.particle = "gamma"
        s.n = 1
        # prepare to run (in a separate process)
        se = gate.SimulationEngine(sim, start_new_process=True)
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
        gamma_final = {}
        for g in self.gammas:
            e = g.transition_energy
            if e in gamma_final:
                gamma_final[e].final_intensity += g.final_intensity
            else:
                gamma_final[e] = g
        self.gammas = []
        for g in gamma_final.values():
            self.gammas.append(g)
        self.gammas = sorted(self.gammas, key=lambda x: x["transition_energy"])

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

        # get all decay channels (firs level)
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
                ch.excitation_energy_label = None
                # get the energy label
                result = re.search(r"(.*)\[(.*)\]", ch.name)
                if result:
                    ch.excitation_energy_label = float(result.groups()[1]) * keV
                channels.append(ch)
        return channels

    def _get_gammas_for_one_channel(self, channel):
        # read database file
        # FIXME: cache it to avoid re-reading ?
        levels = gate.read_level_gamma(channel.a, channel.z)

        # from the name extract the level
        v = self.verbose
        for level in levels.values():
            if level.excitation_energy == channel.excitation_energy_label:
                v and print()
                v and print(f"Analysing channel {channel.name}")
                g = self._get_gammas_for_one_level(levels, level, br=channel.br)
                self.gammas = self.gammas + g

    def _get_gammas_for_one_level(self, levels, level, br, p=1, tab=""):
        g_level = []
        g_level_final = []
        total_p = 0
        if br == 0:
            return g_level_final

        # compute Ig = gamma intensity for all daughters and total Ig
        for d in level.daugthers.values():
            l = self._level_daughter_info(d)
            if l is not None:
                g_level.append(l)
                total_p += l.transition_intensity * (l.alpha + 1)

        if total_p == 0:
            return g_level_final

        # compute the relative intensity
        # consider also the branching ratio and 'p' which is the probability in case
        # of fallback from another level
        v = self.verbose
        keV = gate.g4_units("keV")
        v and print(
            f"{tab}Level = {level.order_level} E={level.excitation_energy/keV} keV  "
            f"nb_levels = {level.n_gammas}  branching_ratio={br:.5f}    current_proba={p:.5f}"
        )
        tab = f"{tab}    "
        for l in g_level:
            l.transition_intensity = (l.alpha + 1) * l.transition_intensity / total_p
            # This is the key computation of the probability
            # P = BR x Pg x It x current_p
            # BR = Branching ratio
            # Pg = gamma emission probability
            # It = total transition probability =  Ic + Ig
            # Ig = transition_intensity
            # alpha = Ic/Ig
            l.final_intensity = l.prob_gamma_emission * l.transition_intensity * br * p
            v and print(
                f"{tab}P{level.order_level}->{l.daughter_order}     E={l.transition_energy/keV} keV "
                f"br={br:.5f}  trans_int = {l.transition_intensity:.5f} {l.prob_gamma_emission:.5f}"
                f"   ->  final intensity = {100*l.final_intensity:.5f}% "
            )
            g_level_final.append(l)
            p2 = l.transition_intensity
            if l.daughter_order != 0:
                l2 = levels[str(l.daughter_order)]
                g = self._get_gammas_for_one_level(levels, l2, br, p2, tab)
                g_level_final = g_level_final + g

        return g_level_final

    def _level_daughter_info(self, d):
        g = Box()
        g.daughter_order = d.daughter_order
        g.transition_energy = d.transition_energy
        g.transition_intensity = d.intensity
        g.alpha = d.alpha
        g.prob_gamma_emission = 1 / (1 + g.alpha)
        return g
