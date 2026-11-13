"""Reusable authored fractured nodule geometry (Blender Python only)."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector

def make_clast_mesh(seed,index):
    bm=bmesh.new();rng=np.random.default_rng(seed+index)
    def fragment(centre,radius,phase):
        count=int(rng.integers(6,10));top=[];bottom=[]
        slope=rng.uniform(-.25,.25,2)
        for k in range(count):
            angle=phase+2*math.pi*k/count;rad=radius*rng.uniform(.72,1.12)
            x=rad*math.cos(angle);y=rad*math.sin(angle)
            z=radius*(.7+slope[0]*x/radius+slope[1]*y/radius+rng.uniform(-.12,.12))
            top.append(bm.verts.new(centre+Vector((x,y,z))))
            bottom.append(bm.verts.new(centre+Vector((x*.8,y*.8,-radius*.45))))
        bm.faces.new(top);bm.faces.new(list(reversed(bottom)))
        for k in range(count):j=(k+1)%count;bm.faces.new([top[k],bottom[k],bottom[j],top[j]])
    fragment(Vector((0,0,0)),.85,rng.uniform(0,6.28))
    for j in range(6):
        angle=rng.uniform(0,2*math.pi);rad=rng.uniform(.3,.85)
        centre=Vector((rad*math.cos(angle),rad*math.sin(angle),rng.uniform(.25,.6)))
        fragment(centre,rng.uniform(.24,.47),rng.uniform(0,6.28))
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    mesh=bpy.data.meshes.new(f'Crumbly aggregate {index}');bm.to_mesh(mesh);bm.free()
    for face in mesh.polygons:face.use_smooth=False
    return mesh
