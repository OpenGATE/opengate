import ast
import inspect
from typing import Callable, Any
from ..utility import g4_units
import opengate_core as g4


# make local variables for each G4 unit
# TODO define guideline for unit naming when * or /
for key in g4_units:
    locals().update({key: g4_units[key]})


class Attribute:
    name: str
    get: Callable[[g4.G4Step], Any]

    def __init__(self, name, get):
        self.name = name
        self.get = get


def attr_particle_name(step: g4.G4Step):
    return g4.GetAttrParticleName(step)
    # return step.GetTrack().GetParticleDefinition().GetParticleName()


# particle_name = Attribute("particle_name", attr_particle_name)
particle_name = Attribute("particle_name", g4.GetAttrParticleName)
pre_kinetic_energy = Attribute("pre_kinetic_energy", g4.GetAttrPreKineticEnergy)


class FilterASTTransformer(ast.NodeTransformer):
    def fn_name_from_attr(self, node):
        f_src = inspect.getsource(eval(ast.unparse(node)).get)
        tree = ast.parse(f_src)
        f_name = tree.body[0].name
        return f_name

    def visit_Name(self, node):
        node_type = eval(f"type({node.id})")
        if node_type is Attribute:
            # Method 1 -- using local functions
            # f_name = self.fn_name_from_attr(node)
            # func = ast.Name(id=f"{f_name}", ctx=ast.Load())

            # Method 2 -- using opengate_core functions
            fn = eval(ast.unparse(node)).get
            print(fn.__module__)

            func = ast.Attribute(
                value=ast.Name(id="opengate_core", ctx=ast.Load()),
                attr=fn.__name__,
                ctx=ast.Load(),
            )

            args = [ast.Name(id="step", ctx=ast.Load())]

            return ast.Call(func=func, args=args, keywords=[])
        else:
            value = eval(ast.unparse(node))
            return ast.Constant(value=value)

    # resolve constant computations (e.g. 5 * MeV)
    def visit_BinOp(self, node: ast.BinOp):
        self.generic_visit(node)
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            value = eval(ast.unparse(node))
            return ast.Constant(value=value)
        else:
            return node

    def visit_Expr(self, node: ast.Expr):
        self.generic_visit(node)
        return node

    def visit_Compare(self, node: ast.Compare):
        self.generic_visit(node)
        return node
