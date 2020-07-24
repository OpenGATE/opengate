import os
import platform
import sys
import logging
import gatetools as gt

log = logging.getLogger(__name__)


def logging_conf(b):
    """
    Sort helper for gatetools logging conf
    """
    gt.logging_conf(b)


def setup_g4_bindings():
    s = platform.system()
    print(f'System {s} python {platform.python_version()}')
    # for name in sys.builtin_module_names:
    #    print(name)
    home_folder = r'D:\David\src'
    g4_folder = home_folder + r'\geant4_10_06-install\bin'
    # gam_g4_folder = home_folder + r'\gate2\gam_g4\cmake-build-debug'
    gam_g4_folder = home_folder + r'\gate2\gam_g4\BIDON'
    g4_data_folder = home_folder + r'\geant4_10_06-install\share\Geant4-10.6.0\data'
    if s == 'Darwin':
        home_folder = '/Users/dsarrut/src/'
        g4_folder = os.path.join(home_folder, 'geant4/geant4.10.06-install/lib')
        # gam_g4_folder = os.path.join(home_folder, 'gate2/gam_g411_build')
        gam_g4_folder = os.path.join(home_folder, 'gate2/gam_g4/cmake-build-release')
        # gam_g4_folder = os.path.join(home_folder, 'gate2/gam_g411/cmake-build-debug')
        g4_data_folder = os.path.join(home_folder, 'geant4/geant4.10.06-install/data')
    if s == 'Linux':
        home_folder = '/home/dsarrut/src/'
        g4_folder = os.path.join(home_folder, 'geant4/geant4.10.06-install/lib64')
        # gam_g4_folder = os.path.join(home_folder, 'gate2/gam_g411_build')
        gam_g4_folder = os.path.join(home_folder, 'gate2/gam_g4/cmake-build-release')
        # gam_g4_folder = os.path.join(home_folder, 'gate2/gam_g411/cmake-build-debug')
        g4_data_folder = os.path.join(home_folder, 'geant4/geant4.10.06/data')
    try:
        print('g4_folder', g4_folder)
        if s == 'Windows':
            os.add_dll_directory(g4_folder)
        else:
            sys.path.append(g4_folder)
        # os.add_dll_directory(r'D:\David\src\gate2\gam_g411\cmake-build-debug')
        print('gam_g4_folder', gam_g4_folder)
        sys.path.append(gam_g4_folder)
    except Exception as e:
        print(e)
        print('Cannot add G4 dll path and/or gam_g4 module ')
        exit(0)
    print('g4_data_folder', g4_data_folder)
    os.environ["G4NEUTRONHPDATA"] = os.path.join(g4_data_folder, r'G4NDL4.6')
    os.environ["G4LEDATA"] = os.path.join(g4_data_folder, r'G4EMLOW7.9')
    os.environ["G4LEVELGAMMADATA"] = os.path.join(g4_data_folder, r'PhotonEvaporation5.5')
    os.environ["G4RADIOACTIVEDATA"] = os.path.join(g4_data_folder, r'RadioactiveDecay5.4')
    os.environ["G4PARTICLEXSDATA"] = os.path.join(g4_data_folder, r'G4PARTICLEXS2.1')
    os.environ["G4PIIDATA"] = os.path.join(g4_data_folder, r'G4PII1.3')
    os.environ["G4REALSURFACEDATA"] = os.path.join(g4_data_folder, r'RealSurface2.1.1')
    os.environ["G4SAIDXSDATA"] = os.path.join(g4_data_folder, r'G4SAIDDATA2.0')
    os.environ["G4ABLADATA"] = os.path.join(g4_data_folder, r'G4ABLA3.1')
    os.environ["G4INCLDATA"] = os.path.join(g4_data_folder, r'G4INCL1.0')
    os.environ["G4ENSDFSTATEDATA"] = os.path.join(g4_data_folder, r'G4ENSDFSTATE2.2')
    print('----------------------------------------------------')
