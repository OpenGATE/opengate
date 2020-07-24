import gam_g4 as g4
import itk

class DoseActor3(g4.GamDoseActor3):
    """
    TODO
    """

    def __init__(self):
        g4.GamDoseActor3.__init__(self)
        self.actions = ['EndOfRunAction']


    def __str__(self):
        s = f'Dose Actor3 '
        return s

    def EndOfRunAction(self, run):
        print('Dose3 end of run')
        #print(type(self.img))
