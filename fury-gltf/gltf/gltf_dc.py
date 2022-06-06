from dataclasses import dataclass
import numpy as np
from fury.lib import PolyData, Texture

@dataclass
class Node:
    meshes: np.ndarray = None


@dataclass
class Mesh:
    primitives: np.ndarray
    name: str = None


@dataclass
class Material:
    baseColorTexture: Texture = None
    metallicRoughnessTexture: Texture = None
    normalTexture: Texture = None
    name:str = None

@dataclass
class Primitive:
    polydata: PolyData
    material: Material = None
















# Dont know if its good for modularity-->
# OR it can helpus in some way
# @dataclass
# class Node:
#     name: str = None
#     camera: np.uint = None
#     mesh: np.uint = None
#     matrix: np.ndarray = None
#     children: np.ndarray = None



# @dataclass
# class Mesh:
#     primitive: Primitive
#     name: str = None
