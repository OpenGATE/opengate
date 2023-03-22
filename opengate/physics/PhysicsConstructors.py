import opengate_core as g4

from .helpers_physics import particle_names_gate2g4

from ..Decorators import requires_fatal
from ..helpers import warning


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

    def close_down(self):
        for v in self.g4_step_limiter_storage.values():
            v = None
        for v in self.g4_special_user_cuts_storage.values():
            v = None
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

        # 'all' overrides individual settings
        if ui.user_limits_particles["all"] is True:
            particle_keys_to_consider = list(ui.user_limits_particles.keys())
        else:
            particle_keys_to_consider = [
                p for p, v in ui.user_limits_particles.items() if v is True
            ]

        if "all" in particle_keys_to_consider:
            particle_keys_to_consider.remove("all")

        # translate to Geant4 particle names
        particles_to_consider = [
            particle_names_gate2g4[k] for k in particle_keys_to_consider
        ]

        g4_particle_table = g4.G4ParticleTable.GetParticleTable()

        # Note: this method should still be extended to make sure all
        # charged particles have some step limit.
        # G4double charge = particle->GetPDGCharge();
        # if(!particle->IsShortLived()) {
        #     if (charge != 0.0 || fApplyToAll) {

        # register StepLimiter as process for relevant particles
        for p_name in particles_to_consider:
            particle = g4_particle_table.FindParticle(particle_name=p_name)
            # FindParticle return nullptr if particle name was not found
            if particle is None:
                warning(f"{p_name} not found")
                continue
            pm = particle.GetProcessManager()

            # G4StepLimiter for the max_step_size cut
            g4_step_limiter = g4.G4StepLimiter("StepLimiter")
            pm.AddDiscreteProcess(g4_step_limiter, 1)

            # G4UserSpecialCuts for the other cuts
            g4_user_special_cuts = g4.G4UserSpecialCuts("UserSpecialCut")
            pm.AddDiscreteProcess(g4_user_special_cuts, 1)

            # store limiter and cuts in lists to
            # to avoid garbage collection after exiting the methods
            self.g4_step_limiter_storage[p_name] = g4_step_limiter
            self.g4_special_user_cuts_storage[p_name] = g4_user_special_cuts
