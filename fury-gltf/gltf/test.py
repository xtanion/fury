from loader import glTFImporter
from fury import utils, window

filename = "fury/fury-gltf/samples/milk-truck/CesiumMilkTruck.gltf"

importer = glTFImporter(filename)
scene = window.Scene()
scene.SetBackground(0.2, 0.2, 0.4)

for pd in importer.primitives:
    actor = utils.get_actor_from_polydata(pd.polydata)
    material = importer.materials[0]
    btexture = material.baseColorTexture

    actor.SetTexture(btexture)

    scene.add(actor)


current_size = (1024, 720)
showm = window.ShowManager(scene, size=current_size)

showm.start()
