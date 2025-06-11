import numpy as np


def read_file(off_file: str):
    vertices = []
    faces = []

    def readline(file):
        line = ""
        while line == "":
            line = file.readline()
            if not line:
                raise EOFError("reached EOF prematurely")
            line = line.strip()
            if line != "" and line[0] == "#":
                line = ""
        return line

    with open(off_file, "r") as file:
        line = readline(file)
        if line != "OFF":
            raise SyntaxError("missing OFF header")

        line = readline(file)
        v, f, _ = [int(n) for n in line.split(" ")]
        vertices = [[float(n) for n in readline(file).split(" ")] for i in range(v)]
        faces = [[int(n) for n in readline(file).split(" ")[1:4]] for i in range(f)]

    return vertices, faces


def write_file(off_file: str, vertices, faces):
    lines = []
    lines.append("OFF\n")
    lines.append(f"{len(vertices)} {len(faces)} 0\n")
    lines.extend([f"{vertex[0]} {vertex[1]} {vertex[2]}\n" for vertex in vertices])
    lines.extend([f"3 {face[0]} {face[1]} {face[2]}\n" for face in faces])

    with open(off_file, "w+") as f:
        f.writelines(lines)


def vectors_from_vertices_faces(vertices, faces):
    # TODO triangular faces assumed for now
    return [[vertices[face[0]], vertices[face[1]], vertices[face[2]]] for face in faces]


# adapter to use OFF files like STL files
# this class replicates parts of stl.mesh.Mesh
class Mesh:
    vectors: []
    cog: []

    def __init__(self, vertices, faces):
        self.vectors = vectors_from_vertices_faces(vertices, faces)
        self._update()

    def from_file(off_file: str):
        vertices, faces = read_file(off_file)
        return Mesh(vertices, faces)

    def get_mass_properties(self):
        return [
            0,  # volume
            self.cog,  # center of gravity
            0,  # inertia matrix expressed at the COG
        ]

    def translate(self, tr):
        self.vectors = [vector + tr for vector in self.vectors]
        self._update()

    def _update(self):
        shape = np.array(self.vectors).shape
        vertices = np.reshape(self.vectors, (shape[0] * shape[1], shape[2]))
        self.cog = np.mean(vertices, axis=0)
