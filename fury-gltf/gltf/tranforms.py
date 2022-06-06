import numpy as np
from scipy.spatial.transform import Rotation as Rot

def translate(translation):
    iden = np.identity(4)
    translation = np.append(translation, 0).reshape(-1, 1)

    t = np.array([[0, 0, 0, 1],
                  [0, 0, 0, 1],
                  [0, 0, 0, 1],
                  [0, 0, 0, 1]], np.float32)
    translation = np.multiply(t, translation)
    translation = np.add(iden, translation)
    
    return translation


def rotate(quat):
    iden = np.identity(3)
    rotation_mat = Rot.from_quat(quat).as_matrix()

    iden = np.append(iden, [[0, 0, 0]]).reshape(-1, 3)

    rotation_mat = np.dot(iden, rotation_mat)
    iden = np.array([[0, 0, 0, 1]]).reshape(-1, 1)

    rotation_mat = np.concatenate((rotation_mat, iden), axis=1)
    return rotation_mat


def scale(scales):
    iden = np.identity(4)
    scales = np.append(scales, [1])

    for i in range (len(scales)):
        iden[i][i] = scales[i]

    return iden


def mat_multiply(arrays):
    iden = np.identity(arrays[0].shape[0])
    for matrix in arrays:
        iden = np.multiply(iden, matrix)

    return iden

def apply_transfomation(vertices, transformation):
    shape = vertices.shape
    t = np.full((shape[0], 1), 1)
    vertices = np.concatenate((vertices, t), axis=1)

    vertices = np.dot(vertices, transformation)
    vertices = vertices[:, :shape[1]]

    return vertices
