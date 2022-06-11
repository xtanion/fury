# GLTF libraries in Python

In this blog I have written my exploration of diffrenent glTF loading libraries in python:
* [panda3d-gltf](https://github.com/Moguri/panda3d-gltf)
* [pyrender](https://github.com/mmatl/pyrender)
* [pygltflib](https://gitlab.com/dodgyville/pygltflib)

## Panda3D-glTF

Panda3D is a popular game engine written in python & C++. Panda3d-gltf adds glTF loading capabilities to the engine. It supports gltf 2.0, glb and gltf extensions. It also has a renderer built in.

The glTF file is processed in `converter.py`. It doesn't use any dataclasses, Most of the data is stored in dictionaries, later converted into `bam` if needed. There's no docs on how to use the viewer and the loader. The `coverter.py` however loads animation data for skeletal animation (inside `load_primitive`) and morph animation. However there seems some bugs with skeletal animations (as mentioned in this [issue](https://github.com/Moguri/panda3d-gltf/issues/62)). 

## Pyrender

Pyrender promises to load various file formats (such as obj, glb, gltf, etc).  It uses PyOpen-gl in the backend.

Most of the glTF models were loaded without any issue, I wasn't able to get a few render a few models with multiples nodes and multiples meshes (The transformation of certain meshes weren't working as they should be).

Many functions uses `@staticmethod` so we can access the classs methods directly. Also, we can modify the Lights or Materials of out model by function call. One of the cool features of pyrender is we can load a model from a url to the source, which is really convenient. Pyrender supports animation by looping through a `while True` loop. It also allows to run a `Viewer` in thread.


## Pygltflib

Pygltflib is by far the most structured gltf library, the only library that uses `dataclasses` it. However the documentation is not that good. It does not contain any scene viewer, so we can only extract the data from it and use it in any renderer. It can also create/modify gltf file from python functions supports both `.gltf` and `.glb` file formats. 

Doc mentions that it has animation support however I wasn't able to find how to extract `skin` and `morph` information from gltf 2.0 files (also mentioned in this [issue](https://gitlab.com/dodgyville/pygltflib/-/issues/49)). Pygltflib can access the extensions data as well. We can call the `gltf` data class or each module seperately if we needed. 