import opengate_core as g4

from .helpers_physics import translate_particle_name_gate2G4

from ..Decorators import requires_fatal
from ..helpers import warning, fatal


class UserLimitsPhysics(g4.G4VPhysicsConstructor):
    """
    Class to be registered to physics list.

    It is essentially a refined version of StepLimiterPhysics which considers the user's
    particles choice of particles to which the step limiter should be added.

    """

    def __init__(self):
        """Objects of this class are created via the PhysicsEngine class.
        The user should not create objects manually.

        """
        g4.G4VPhysicsConstructor.__init__(self, "UserLimitsPhysics")
        self.physics_engine = None

        self.g4_step_limiter_storage = {}
        self.g4_special_user_cuts_storage = {}

        print("UserLimitsPhysics.__init__")

    def close(self):
        self.g4_step_limiter_storage = None
        self.g4_special_user_cuts_storage = None

    @requires_fatal("physics_engine")
    def ConstructParticle(self):
        """Needs to be defined because C++ base class declares this as purely virtual member."""
        pass

    @requires_fatal("physics_engine")
    def ConstructProcess(self):
        """Overrides method from G4VPhysicsConstructor
        that is called when the physics list is constructed.

        """
        ui = self.physics_engine.user_info_physics_manager

        particle_keys_to_consider = []
        # 'all' overrides individual settings
        if ui.user_limits_particles["all"] is True:
            particle_keys_to_consider = list(ui.user_limits_particles.keys())
        else:
            keys_to_exclude = ("all", "all_charged")
            particle_keys_to_consider = [
                p
                for p, v in ui.user_limits_particles.items()
                if v is True and p not in keys_to_exclude
            ]

        if len(particle_keys_to_consider) == 0:
            warning(
                "user_limits_particles is False for all particles. No tracking cuts will be applied. Use Simulation.set_user_limits_particles()."
            )

        # translate to Geant4 particle names
        particles_to_consider = [
            translate_particle_name_gate2G4(k) for k in particle_keys_to_consider
        ]

        for particle in g4.G4ParticleTable.GetParticleTable().GetParticleList():
            add_step_limiter = False
            add_user_special_cuts = False
            p_name = str(particle.GetParticleName())

            if p_name in particles_to_consider:
                add_step_limiter = True
                add_user_special_cuts = True

            # this reproduces the logic of the Geant4's G4StepLimiterPhysics class
            if (
                ui.user_limits_particles["all_charged"] is True
                and particle.GetPDGCharge() != 0
            ):
                add_step_limiter = True

            if add_step_limiter is True or add_user_special_cuts is True:
                pm = particle.GetProcessManager()
                if add_step_limiter is True:
                    # G4StepLimiter for the max_step_size cut
                    g4_step_limiter = g4.G4StepLimiter("StepLimiter")
                    pm.AddDiscreteProcess(g4_step_limiter, 1)
                    # store limiter and cuts in lists to
                    # to avoid garbage collection after exiting the methods
                    self.g4_step_limiter_storage[p_name] = g4_step_limiter
                if add_user_special_cuts is True:
                    # G4UserSpecialCuts for the other cuts
                    g4_user_special_cuts = g4.G4UserSpecialCuts("UserSpecialCut")
                    pm.AddDiscreteProcess(g4_user_special_cuts, 1)
                    self.g4_special_user_cuts_storage[p_name] = g4_user_special_cuts
