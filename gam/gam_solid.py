

def G4Box_builder(v):
    if 'size' not in v:
        try:
            for i in range(3):
                v.size[i] = v.half_size[i]*2
        except:
            print('ERROR, cannot find half_size')
    else:
        # size takes prior to half_size
        if 'half_size' in v:
            print('Warning recompute half_size from size')
        try:
            v.half_size = [0,0,0]
            for i in range(3):
                v.half_size[i] = v.size[i]/2.0
        except:
            print('ERROR, cannot find size', v)
            exit()
    hx = v.half_size[0]
    hy = v.half_size[1]
    hz = v.half_size[2]
    return G4Box_fake(v.name, hx, hy, hz)


def G4Box_fake(name, x_half_length, y_half_length, z_half_length):
    # solid = Geant4.G4Box(name, x_half_length, y_half_length, z_half_length)
    print('New G4Box,', name, x_half_length, y_half_length, z_half_length)
    return 'volume_constructed'


'''
Global list of volume builder
'''
g_solid_builders = {}
g_solid_builders['Box'] = G4Box_builder

