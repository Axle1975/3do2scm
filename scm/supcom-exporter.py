#**************************************************************************************************
# Adapted from: Supreme Commander Exporter for Blender3D - www.blender3d.org
#
# Written by dan - www.sup-com.net), Brent (www.scmods.net)
#
# further improvements by GeomanNL and Darius
#
# History
#
# 0.1.0  2006-07-02 Dan Initial version.
#
# 0.2.0   2007-03-11    Brent Fixed UV coords, V was inverted.
#               Support for exporting quads.
#               Fixed a padding issue.
#
# 0.3.0   2007-03-18    Dan Code refactoring / Clean up.
#               Fixed 'INFO' section size in header.
#
# 0.3.3  2007-09-25 GeomanNL  fixed a file-write bug
#               orientation fix, changed to matrix rotation
#               other excellent stuff
#               (me darius took the freedom to write your entry:D)
#
# 0.3.5  2009-03-20 Darius_  tangent and binormal calc
#               vertex optimation
#               blender front to supcom front
#               some more fixes and reorganizing/cleanup code
#
# 0.4.0  2014-07-13 Oygron   Script ported to Blender 2.71
#
#
# Todo
#   - GUI improvements
#   - Support for LOD exporting. Eg. not merging all meshes for an armature into one mech but rather only
#     sub-meshes and export the top level meshes to different files.
#   - Validation, ensure that
#     - Prompt before overwriting files & check that directories exists
#   - Second UV set?
#   - Set animation time per frame
#   - Export LUA script for use in the animation viewer (eg, start anim, set texture etc)..
#   - Set root rot/pos for sca
#   - Progress bar
#
#**************************************************************************************************


import os
from os import path

import struct
import string
import math
from math import *

from string import *
from struct import *

import json
import sys

LOG_VERT = False
LOG_BONE = False
VERTEX_OPTIMIZE=True


######################################################
# Init Supreme Commander SCM( _bone, _vertex, _mesh), SCA(_bone, _frame, _anim) Layout
######################################################


def cross(a, b):
    c = [a[1]*b[2] - a[2]*b[1],
         a[2]*b[0] - a[0]*b[2],
         a[0]*b[1] - a[1]*b[0]]
    return c


def mag(v):
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])


def normalize(v):
    magv = mag(v)
    if magv>0.:
        return [ float(vi)/magv for vi in v ]
    else:
        return v


class scm_bone :

    rest_pose = []
    rest_pose_inv = []
    rotation = []
    position = []
    parent_index = 0
    keyed = False
    name = ""

    def __init__(self, name, rest_pose_inv, rotation, position, parent_index):

        self.rest_pose_inv = rest_pose_inv
        self.rotation = rotation
        self.position = position
        self.parent_index = parent_index
        self.keyed = False
        self.name = name


    def save(self, file):
        bonestruct = '16f3f4f4i'
        #bonestruct = '16f3f4f4L' #Deprecation warning L and mistyrious binary output
        rp_inv = [0] * 16

        icount = 0
        for irow in range(4):
            #rest pose_inv
            for icol in range(4):
                rp_inv[icount] = self.rest_pose_inv[irow][icol]
                icount = icount + 1

        bonedata = struct.pack(bonestruct,
            rp_inv[0], rp_inv[1], rp_inv[2], rp_inv[3],
            rp_inv[4], rp_inv[5], rp_inv[6], rp_inv[7],
            rp_inv[8], rp_inv[9], rp_inv[10],rp_inv[11],
            rp_inv[12],rp_inv[13],rp_inv[14],rp_inv[15],
            self.position[0],self.position[1],self.position[2],
            self.rotation[0],self.rotation[1],self.rotation[2],self.rotation[3], #Quaternion (w,x,y,z)#w,x,y,z
            self.name_offset, self.parent_index,
            0,0)


        if LOG_BONE :
            print(" %s rp_inv: [%.3f, %.3f, %.3f, %.3f],\t [%.3f, %.3f, %.3f, %.3f],\t [%.3f, %.3f, %.3f, %.3f],\t [%.3f, %.3f, %.3f, %.3f] \tpos: [%.3f, %.3f, %.3f] \trot: [%.3f, %.3f, %.3f, %.3f] %d"
            % ( self.name, rp_inv[0], rp_inv[1], rp_inv[2], rp_inv[3],
                rp_inv[4], rp_inv[5], rp_inv[6], rp_inv[7],
                rp_inv[8], rp_inv[9], rp_inv[10],rp_inv[11],
                rp_inv[12],rp_inv[13],rp_inv[14],rp_inv[15],
                self.position[0],self.position[1],self.position[2],
                self.rotation[0],self.rotation[1],self.rotation[2],self.rotation[3], self.parent_index))


        file.write(bonedata)


class scm_vertex :

    position = []
    tangent  = []
    normal   = []
    binormal = []
    uvc = 0
    uv1 = []
    uv2 = []
    bone_index = []

    def __init__(self, pos , no , uv1, bone_index):

        self.position = pos
        self.normal   = no

        #tangent and binormal wil be calculated by face
        self.tangent  = [ 0, 0, 0 ]
        self.binormal = [ 0, 0, 0 ]

        self.uvc = 1
        self.uv1 = uv1
        self.uv2 = uv1# Vector(0,0) #uv1 #better results with copy ... strange, where is the use of that?

        self.bone_index = bone_index


    def save(self, file):

        vertstruct = '3f3f3f3f2f2f4B'

        #so finaly we can norm because here it is sure that no tang norm will be added
        #self.normal = CrossVecs(self.tangent, self.binormal).normalize()
        self.tangent = normalize(self.tangent)
        self.binormal = normalize(self.binormal)
        self.normal = normalize(self.normal)

        if LOG_VERT :
            print( " pos: [%.3f, %.3f, %.3f] \tn: [%.3f, %.3f, %.3f] \tt: [%.3f, %.3f, %.3f] \tb: [%.3f, %.3f, %.3f] \tuv [ %.3f, %.3f | %.3f, %.3f ] \tbi: [%d, %d, %d, %d]"

            % (
                self.position[0], self.position[1], self.position[2],
                self.normal[0],   self.normal[1],   self.normal[2],
                self.tangent[0],  self.tangent[1],  self.tangent[2],
                self.binormal[0], self.binormal[1], self.binormal[2],
                self.uv1[0], self.uv1[1],
                self.uv2[0], self.uv2[1],
                self.bone_index[0], self.bone_index[1],
                self.bone_index[2], self.bone_index[3]) )

        # so you store in this order:
        # pos, normal, tangent, binormal, uv1, uv2, ibone
        vertex = struct.pack(vertstruct,
            self.position[0], self.position[1], self.position[2],
            self.normal[0],   self.normal[1],   self.normal[2],
            self.tangent[0],  self.tangent[1],  self.tangent[2],
            self.binormal[0], self.binormal[1], self.binormal[2],
            self.uv1[0], self.uv1[1],
            self.uv2[0], self.uv2[1],
            self.bone_index[0] or 0, self.bone_index[1] or 0,
            self.bone_index[2] or 0, self.bone_index[3] or 0)


        file.write(vertex)

#helper the real scm face 'tupel is stored in mesh
#quad face
class qFace :

        vertex_cont = []

        def __init__(self):
            self.vertex_cont = []

        def addVert(self, vertex):
            self.vertex_cont.extend( vertex )

        def addToMesh(self, mesh):

            face1 = Face()
            face1.addVert([ self.vertex_cont[0], self.vertex_cont[1], self.vertex_cont[2] ])
            face1.CalcTB()

            face2 = Face()
            face2.addVert([ self.vertex_cont[2], self.vertex_cont[3], self.vertex_cont[0] ])
            face2.CalcTB()

            mesh.addQFace(face1, face2)


#helper the real scm face 'tupel is stored in mesh
#tri face
class Face :

    vertex_cont = []

    def __init__(self):
        self.vertex_cont = []

    def addVert(self, vertex):
        self.vertex_cont.extend(vertex)

    #now contains 3 vertexes calculate bi and ta and add to mesh

    def CalcTB( self ) :
        vert1 = self.vertex_cont[0]
        vert2 = self.vertex_cont[1]
        vert3 = self.vertex_cont[2]

        uv = [ vert1.uv1, vert2.uv1, vert3.uv1]

        # Calculate Tangent and Binormal
        #       (v3 - v1).(p2 - p1) - (v2 - v1).(p3 - p1)
        #   T  =  ------------------------------------------------
        #       (u2 - u1).(v3 - v1) - (v2 - v1).(u3 - u1)
        #       (u3 - u1).(p2 - p1) - (u2 - u1).(p3 - p1)
        #   B  =  -------------------------------------------------
        #       (v2 - v1).(u3 - u1) - (u2 - u1).(v3 - v1)

        P2P1 = diff(vert2.position, vert1.position)
        P3P1 = diff(vert3.position, vert1.position)

        #UV2UV1 = [ uv[1][0]-uv[0][0], uv[1][1]-uv[0][1] ]
        #UV3UV1 = [ uv[2][0]-uv[0][0], uv[2][1]-uv[0][1] ]

        UV2UV1 = diff(uv[1], uv[0])
        UV3UV1 = diff(uv[2], uv[0])
        divide = (UV2UV1[1]*UV3UV1[0] - UV2UV1[0]*UV3UV1[1])

        if ( divide != 0.0 ) :
            tangent = [  UV3UV1[1]*p/divide - UV2UV1[1]*q/divide for p,q in zip(P2P1,P3P1) ]
            binormal =[ -UV3UV1[0]*p/divide + UV2UV1[0]*q/divide for p,q in zip(P2P1,P3P1) ]
            #tangent = Vector((UV3UV1[1]*P2P1 - UV2UV1[1]*P3P1)/(divide))
            #binormal =Vector((UV3UV1[0]*P2P1 - UV2UV1[0]*P3P1)/(-divide))

        else :
            #print("Vertex-T-B divided through zero")
            #print("  vert1.uv1:{}, vert2.uv1:{}, vert3.uv1:{}".format(vert1.uv1, vert2.uv1, vert3.uv1))
            tangent = [0.,0.,0.]
            binormal = [0.,0.,0.]

        #add calculated tangent and binormal to vertices
        for ind in range(3):
            self.vertex_cont[ind].tangent = tangent
            self.vertex_cont[ind].binormal =  binormal

    def addToMesh( self, mesh ) :
        self.CalcTB()
        mesh.addFace( self )



# Helper methods
######################################################

def pad(size):
    val = 32 - (size % 32)
    if (val < 4):
        val = val + 32

    return val

def pad_file(file, s4comment):
    N = pad(file.tell()) - 4
    filldata = b'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    padding = struct.pack(str(N)+'s4s', filldata[0:N], s4comment)

    file.write(padding)

    return file.tell()

#
######################################################


class scm_mesh :

    bones = []
    vertices = []
    vertcounter = 0
    faces = []
    info = []

    def __init__(self):
        self.bones = []
        self.vertices = []
        self.faces = []
        self.info = []
        self.vertcounter = 0

    def _addVert( self, nvert ):
        if VERTEX_OPTIMIZE :
            #search for vertex already in list
            vertind = 0
            fiddleVertex = True
            for vert in self.vertices :
                if nvert.uv1 == vert.uv1 and nvert.position == vert.position :
                    if nvert.bone_index == vert.bone_index:
                        break   #found vert in list keep that index
                    else:
                        fiddleVertex = True
                vertind += 1 #hmm not that one

            if vertind == len(self.vertices):
                if fiddleVertex:
                    nvert = scm_vertex(
                        [x+float(vertind)/100000. for x in nvert.position],
                        nvert.normal, nvert.uv1, nvert.bone_index)
                self.vertices.append(nvert)
            else:
                vert = self.vertices[vertind]

                vert.tangent = [ t1+t2 for t1,t2 in zip(vert.tangent,nvert.tangent) ]
                vert.binormal = [ b1+b2 for b1,b2 in zip(vert.binormal,nvert.binormal) ]
                vert.normal = [ n1+n2 for n1,n2 in zip(vert.normal,nvert.normal) ]
                self.vertices[vertind] = vert

            return vertind
        else:
            self.vertices.append(nvert)
            return len(self.vertices)-1

    def addFace( self, face ):

        facein = [ self._addVert(nvert) for nvert in face.vertex_cont]
        self.faces.append(facein)

    def addQFace( self, face1, face2):

        facein = [ self._addVert(nvert) for nvert in face1.vertex_cont]
        self.faces.append(facein)

        facein = [ facein[2], self._addVert(face2.vertex_cont[1]), facein[0]]
        self.faces.append(facein)


    def save(self, filename):

        scm = open(filename, 'wb')


        #headerstruct = '12L' #Deprecation warning L and mistyrious binary output

        headerstruct = '4s11I'
        headersize = struct.calcsize(headerstruct)

        #marker = 'MODL'
        marker = b'MODL'
        version = 5
        boneoffset = 0
        bonecount = 0
        vertoffset = 0
        extravertoffset = 0
        vertcount = len(self.vertices)
        indexoffset = 0
        indexcount = len(self.faces) * 3
        infooffset = 0
        infosize = 0
        totalbonecount = len(self.bones)



        # Write dummy header
        header = struct.pack(headerstruct + '',
            marker, version, boneoffset, bonecount, vertoffset,
            extravertoffset, vertcount, indexoffset, indexcount,
            infooffset, infosize, totalbonecount)

        scm.write(header)


        # Write bone names
        pad_file(scm, b'NAME')

        for bone in self.bones:
            bone.name_offset = scm.tell()
            name = bone.name
            buffer = struct.pack(str(len(name) + 1)+'s', name.encode('utf-8')) #bytearray(name,'ascii'))
            scm.write(buffer)
            #Log(buffer)

        # Write bones
        boneoffset = pad_file(scm, b'SKEL')

        for bone in self.bones:
            bone.save(scm)
            # if bone.used == True:
            bonecount = bonecount + 1




        # Write vertices
        vertoffset = pad_file(scm, b'VTXL')

        for vertex in self.vertices:
            vertex.save(scm)



        # Write Faces
        indexoffset = pad_file(scm, b'TRIS')

        for f in range(len(self.faces)):
            face = struct.pack('3H', self.faces[f][0], self.faces[f][1], self.faces[f][2])
            #face = struct.pack('3h', self.faces[f][0], self.faces[f][1], self.faces[f][2])
            scm.write(face)


        #print( "Bones: %d, Vertices: %d, Faces: %d; \n" % (bonecount, len(self.vertices), len(self.faces)))

        #Write Info
        if len(self.info) > 0:

            infooffset = pad_file(scm, b'INFO')

            for i in range(len(self.info)):
                info = self.info[i]
                infolen = len(info) + 1
                buffer = struct.pack(str(infolen)+'s', bytearray(info,'ascii'))
                scm.write(buffer)

            infosize = scm.tell() - infooffset;

        # Now we can update the header
        scm.seek(0, 0)

        header = struct.pack(headerstruct,
            marker, version, boneoffset, bonecount, vertoffset,
            extravertoffset, vertcount, indexoffset, indexcount,
            infooffset, infosize, totalbonecount)

        scm.write(header)

        scm.close()



######################################################
# Exporter Functions
######################################################

def make_scm_bone(_3do_obj, parent_bone, parent_bone_index):

    name = _3do_obj["name"]
    rotation = [1,0,0,0]

    position = [ _3do_obj[k] for k in ['x','y','z'] ]
    if parent_bone is not None:
        position = [ p+q for p,q in zip(position,parent_bone.position) ]

    rest_pose = [[ 1, 0, 0, 0],
                 [ 0, 1, 0, 0],
                 [ 0, 0, 1, 0],
                 [ position[0], position[1], position[2], 1]]

    rest_pose_inv = [[ 1, 0, 0, 0],
                 [ 0, 1, 0, 0],
                 [ 0, 0, 1, 0],
                 [ -position[0], -position[1], -position[2], 1]]

    return scm_bone(name, rest_pose_inv, rotation, position, parent_bone_index)


def diff(x1,x2):
    return [ u-v for u,v in zip(x1,x2) ]


def get_face_normal(vert1, vert2, vert3, vert4=None):

    if vert4 is None:
        try_pairs = [
            [diff(vert2,vert1),diff(vert3,vert2)],
            [diff(vert3,vert2),diff(vert1,vert3)],
            [diff(vert1,vert3),diff(vert2,vert1)] ]

    else:
        try_pairs = [
            [diff(vert2,vert1),diff(vert3,vert2)],
            [diff(vert3,vert2),diff(vert4,vert3)],
            [diff(vert4,vert3),diff(vert1,vert4)],
            [diff(vert1,vert4),diff(vert2,vert1)] ]

    for u,v in try_pairs:
        uxv = cross(u,v)
        uvMag = mag(uxv)
        uMag = mag(u)
        vMag = mag(v)
        if uvMag<=1e-3*uMag or uvMag<=1e-3*vMag:
            continue

        return [float(uxv[0])/uvMag, float(uxv[1])/uvMag, float(uxv[2])/uvMag]

    return [0.,0.,1.]


def get_obj_vertices_list(_3do_vertices, offset_position):
    return [
        [offset_position[0]+vertex['x'], offset_position[1]+vertex['y'], offset_position[2]+vertex['z']]
        for vertex in _3do_vertices
    ]


def make_scm_face(object_vertex_list, face_vertex_indices, uvmin, uvmax, parent_bone_index):

    umin,vmin = uvmin
    umax,vmax = uvmax

    if len(face_vertex_indices) > 4:
        face_vertex_indices = face_vertex_indices[0:4]

    if len(face_vertex_indices) == 4:
        new_scm_face = qFace()
        uv_list = [[umin,vmax], [umax,vmax], [umax,vmin], [umin,vmin]]

    elif len(face_vertex_indices) == 3:
        new_scm_face = Face()
        uv_list = [[umin,vmax], [umax,vmax], [umin,vmin]]

    else:
        raise ValueError("unexpected number of vertices in facet: {}".format(len(face_vertex_indices)))

    normal = get_face_normal(*[object_vertex_list[i] for i in face_vertex_indices])

    scm_vertex_list = [
        scm_vertex(object_vertex_list[idxVert], normal, uv, [parent_bone_index,0,0,0])
        for idxVert,uv in zip(face_vertex_indices,uv_list) ]

    new_scm_face.addVert(scm_vertex_list)
    return new_scm_face


def recursive_count_faces(_3do_obj):

    this_object_face_count = len(_3do_obj["primitives"])
    children_face_count = [ recursive_count_faces(_3do_child) for _3do_child in _3do_obj["children"] ]
    return sum(children_face_count) + this_object_face_count


def recursive_append_3do(scm_mesh, _3do_obj, parent_bone, parent_bone_index):

    new_bone_index = len(scm_mesh.bones)
    new_scm_bone = make_scm_bone(_3do_obj, parent_bone, parent_bone_index)
    scm_mesh.bones.append(new_scm_bone)

    vertex_list = get_obj_vertices_list(_3do_obj["vertices"], new_scm_bone.position)

    for _3do_primitive in _3do_obj["primitives"]:
        try:
            vertex_indices = _3do_primitive["vertices"]
            uvmin = _3do_primitive["uvmin"]
            uvmax = _3do_primitive["uvmax"]
            new_scm_face = make_scm_face(vertex_list, vertex_indices, uvmin, uvmax, new_bone_index)
            new_scm_face.addToMesh(scm_mesh)

        except ValueError as e:
            print(repr(e))

    for _3do_child in _3do_obj["children"]:
        recursive_append_3do(scm_mesh, _3do_child, new_scm_bone, new_bone_index)


def make_scm(_3do_obj):

    total_face_count = recursive_count_faces(_3do_obj)
    tileDimension = int(0.5+math.sqrt(total_face_count))
    supcom_mesh = scm_mesh()
    recursive_append_3do(supcom_mesh, _3do_obj, None, 0)
    return supcom_mesh


def recursive_coordinate_transform(_3do_obj):

    def do_transform(_3do_coordinates):
        _3do_coordinates["x"] /= 2.5
        _3do_coordinates["y"] /= 2.5
        _3do_coordinates["z"] /= -2.5

    do_transform(_3do_obj)

    for vert in _3do_obj["vertices"]:
        do_transform(vert)

    for prim in _3do_obj["primitives"]:
        # do_transform flips the handedness.  so we need to flip the normals back again
        prim["vertices"].reverse()

    for child in _3do_obj["children"]:
        recursive_coordinate_transform(child)


if __name__ == "__main__":

    _3do_data = json.load(sys.stdin)
    for k,v in _3do_data.items():
        print("processing {}".format(k))
        recursive_coordinate_transform(v[0])
        supcom_mesh = make_scm(v[0])
        supcom_mesh.save("{}_lod0.scm".format(k))
    print("Done!")
