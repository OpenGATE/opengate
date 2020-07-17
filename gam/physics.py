from box import Box
import gam
import gam_g4 as g4


def create_phys_list(physics):
    # set physics list
    factory = g4.G4PhysListFactory()
    phys_list = factory.GetReferencePhysList(physics.name)
    # FIXME check if exist
    # FIXME EM only PL to create
    return phys_list


def set_cuts(physics, g4_PhysList):
    # set cuts
    # g4_PhysList.DumpList()
    # g4_PhysList.DumpCutValuesTable(1)
    print('default cut value', g4_PhysList.GetDefaultCutValue())
    pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
    print('pct', pct)
    eV = gam.g4_units('eV')
    GeV = gam.g4_units('GeV')
    pct.SetEnergyRange(250 * eV, 100 * GeV)
    print('default cut value', g4_PhysList.GetDefaultCutValue())
