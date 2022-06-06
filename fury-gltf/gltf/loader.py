import base64
import numpy as np
import json as j
import os

from fury import utils
from fury.lib import PNGReader, Texture, JPEGReader, ImageFlip
import tranforms
from gltf_dc import *


comp_type = {
    '5120': {'size': 1, 'dtype': np.byte},
    '5121': {'size': 1, 'dtype': np.ubyte},
    '5122': {'size': 2, 'dtype': np.short},
    '5123': {'size': 2, 'dtype': np.ushort},
    '5125': {'size': 4, 'dtype': np.uint},
    '5126': {'size': 4, 'dtype': np.float32}
}

acc_type = {
    'SCALAR': 3,
    'VEC2': 2,
    'VEC3': 3
}

class glTFImporter():
    
    
    def __init__(self, filename):
        
        fp = open(filename)
        self.json = j.load(fp)
        fp.close()

        gltf = filename.split('/')[-1:][0]
        self.pwd = filename[:-len(gltf)]

        self.materials = {}
        self.nodes = {}
        self.meshes = {}
        self.primitives = []
        self.cameras = {}
        self.transforms = {}
        self.init_transform = np.identity(4)
        self.get_nodes(0)   
    
    
    def get_nodes(self, scene_id):
        scene = self.json['scenes'][scene_id]
        nodes = scene.get('nodes')
        
        for node_id in nodes:
            print(f'Node: {node_id}')
            self.transverse_node(node_id, self.init_transform)
    
    
    def transverse_node(self, nextnode_id, matrix):
        node = self.json['nodes'][nextnode_id]
        
        matnode = np.identity(4)
        if 'matrix' in node:
            matnode = np.array(node['matrix'])
            matnode = matnode.reshape(-1, 4)
        else:
            if 'translation' in node:
                trans = node['translation']
                T = tranforms.translate(trans)
                matnode = np.dot(matnode, T)

            if 'rotation' in node:
                rot = node['rotation']
                R = tranforms.rotate(rot)
                matnode = np.dot(matnode, R)

            if 'scale' in node:
                scales = node['scale']
                S = tranforms.scale(scales)
                matnode = np.dot(matnode, S)

        next_matrix = np.dot(matrix, matnode)
        
        if 'mesh' in node:
            mesh_id = node['mesh']
            mesh = self.load_mesh(mesh_id, next_matrix)
            self.meshes['mesh_id'] = mesh
            self.transforms['mesh_id'] = next_matrix
        
        if 'camera' in node:
            camera_id = node['camera']
            # Todo -->
            # camera = load_camera(camera_id)

        if node.get('children'):
            for child_id in node['children']:
                self.transverse_node(child_id, next_matrix)

    
    def load_mesh(self, mesh_id, transform):
        primitives = self.json['meshes'][mesh_id]['primitives']

        for primitive in primitives:
            
            position_id = primitive['attributes'].get('POSITION')
            normal_id = primitive['attributes'].get('NORMAL')
            texcoord_id = primitive['attributes'].get('TEXCOORD_0')
            indices_id = primitive.get('indices')
            material_id = primitive.get('material')

            vertices = self.get_acc_data(position_id)
            indices = self.get_acc_data(indices_id)
            uv = self.get_acc_data(texcoord_id)

            # Applying transformation
            vertices = tranforms.apply_transfomation(vertices, transform.T)
            
            if material_id!=None:
                material = self.get_materials(material_id)
                self.materials[mesh_id] = material

            polydata = utils.PolyData()

            utils.set_polydata_vertices(polydata, vertices)
            utils.set_polydata_triangles(polydata, indices)
            polydata.GetPointData().SetTCoords(utils.numpy_support.numpy_to_vtk(uv))

            prim = Primitive(polydata)
            self.primitives.append(prim)


    def get_acc_data(self, acc_id):
        
        accessor = self.json['accessors'][acc_id]
        
        buffview_id = accessor.get('bufferView')
        acc_byte_offset = accessor.get('byteOffset', 0)
        d_type = comp_type.get(str(accessor['componentType']))
        a_type = acc_type.get(accessor['type'])

        buffview = self.json['bufferViews'][buffview_id]

        buff_id = buffview['buffer']
        byte_offset = buffview.get('byteOffset', 0)
        byte_length = buffview['byteLength']
        byte_stride = buffview.get('byteStride', a_type * d_type['size'])

        total_byte_offset = byte_offset + acc_byte_offset
        byte_length = byte_length - acc_byte_offset

        return self.get_buff_array(buff_id, d_type['dtype'], byte_length, total_byte_offset, byte_stride)

    
    def get_buff_array(self, buff_id, d_type, byte_length, byte_offset, byte_stride=6):

        uri = self.json["buffers"][buff_id]['uri']
        dtype = np.dtype('B')

        if d_type == np.short or d_type == np.ushort:
            byte_length = int(byte_length/2)
            byte_stride = int(byte_stride/2)

        elif d_type == np.float32 or d_type == np.uint16:
            byte_length = int(byte_length/4)
            byte_stride = int(byte_stride/4)

        try:
            if uri.startswith('data:application/octet-stream;base64') or \
                    uri.startswith('data:application/gltf-buffer;base64'):
                buff_data = uri.split(',')[1]
                buff_data = base64.b64decode(buff_data)

            elif uri.endswith('.bin'):
                with open(os.path.join(self.pwd, uri), 'rb') as f:
                    buff_data = f.read(-1)

            out_arr = np.frombuffer(buff_data, dtype=d_type,
                                    count=byte_length, offset=byte_offset)

            out_arr = out_arr.reshape(-1, byte_stride)
            return out_arr

        except IOError:
            print('Failed to read ! Error in opening file')

    
    def get_materials(self, mat_id):
        
        print(f'Fetching Material...{mat_id}')
        material = self.json.get('materials')[mat_id]
        bct, mrt, nt = None, None, None

        if 'pbrMetallicRoughness' in material:
            pbr = material['pbrMetallicRoughness']
            
            if 'baseColorTexture' in pbr:
                bct = pbr['baseColorTexture']['index']
                bct = self.get_texture(bct)

            if 'metallicRoughnesstexture' in pbr:
                mrt = pbr['metallicRoughnessTexture']['index']
                mrt = self.get_texture(mrt)
        if 'normalTexture' in material:
            nt = material['normalTexture']['index']
            nt = self.get_texture(nt)

        return Material(bct, mrt, nt)
        
    
    def get_texture(self, tex_id):

        textures = self.json.get('textures')
        images = self.json.get('images')

        reader_type = {
            '.jpg': JPEGReader,
            '.png': PNGReader
        }
        filename = images[textures[tex_id]['source']]['uri']
        extension = os.path.splitext(os.path.basename(filename).lower())[1]

        reader = reader_type.get(extension)()
        reader.SetFileName(os.path.join(self.pwd, filename))
        reader.Update()

        flip = ImageFlip()
        flip.SetInputConnection(reader.GetOutputPort())
        flip.SetFilteredAxis(1)  # flip along Y axis

        atexture = Texture()
        atexture.InterpolateOn()
        atexture.EdgeClampOn()
        atexture.SetInputConnection(flip.GetOutputPort())

        return atexture



