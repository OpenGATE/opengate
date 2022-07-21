from .HitsCollectionActor import *


class ARFTrainingDatasetActor(g4.GamARFTrainingDatasetActor, gam.ActorBase):
    """
    FIXME


    Note: Must inherit from ActoBase not from HitsCollectionActor, even if the
    cpp part inherit from HitsCollectionActor

    """

    type_name = 'ARFTrainingDatasetActor'

    @staticmethod
    def set_default_user_info(user_info):
        HitsCollectionActor.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = 'arf_training.root'
        user_info.debug = False
        user_info.energy_windows_actor = None
        user_info.russian_roulette = 1

    def __init__(self, user_info):
        print('ARFTrainingDatasetActor init')
        gam.ActorBase.__init__(self, user_info)
        g4.GamARFTrainingDatasetActor.__init__(self, user_info.__dict__)

    def __del__(self):
        pass

    def __str__(self):
        s = f'ARFTrainingDatasetActor {self.user_info.name}'
        return s
