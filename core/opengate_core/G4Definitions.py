import os

g4_particle_names = []
p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "geant4_particles.txt")
with open(p, "r") as f:
    lines = f.readlines()
    for l in lines:
        if not l.startswith("#"):
            g4_particle_names.extend([p.strip() for p in l.split(",")])
