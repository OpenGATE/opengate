import gam_gate as gam
import gam_g4 as g4


class HitsAdderActor(g4.GamHitsAdderActor, gam.ActorBase):
    """
    Equivalent to Gate "adder": gather all hits of an event in the same volume.
    Input: a HitsCollection, need aat least TotalEnergyDeposit and PostPosition attributes
    Output: a Single collections

    Policies:
    - TakeEnergyWinner: consider position and energy of the hit with the max energy
       -> all other attributes (Time, etc): the value of the winner is used.
    - TakeEnergyCentroid: computed the energy-weighted centroid
       -> all other attributes (Time, etc): the value the last seen hit is used.

    """

    type_name = 'HitsAdderActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = 'singles.root'
        user_info.input_hits_collection = 'Hits'
        user_info.policy = 'TakeEnergyWinner'
        user_info.skip_attributes = []

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamHitsAdderActor.__init__(self, user_info.__dict__)
        actions = {'StartSimulationAction', 'EndSimulationAction'}
        self.AddActions(actions)
        self.fStepFillNames = user_info.attributes

    def __del__(self):
        pass

    def __str__(self):
        s = f'HitsAdderActor {self.user_info.name}'
        return s

    def StartSimulationAction(self):  # not needed, only if need to do something in python
        g4.GamHitsAdderActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GamHitsAdderActor.EndSimulationAction(self)
