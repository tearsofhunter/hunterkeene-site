"""Kodolu Maja at sunset. Usage: python scene2.py OUT.png [angle_deg] [samples] [width] [frame_phase 0..1]"""
import bpy, bmesh, math, sys, mathutils
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
KM='/tmp/claude-0/-home-claude/4f37e95d-919e-58a9-8612-3aeead9a426c/scratchpad/km/split.glb'
out=sys.argv[1]; ang=float(sys.argv[2]) if len(sys.argv)>2 else 150; spp=int(sys.argv[3]) if len(sys.argv)>3 else 64
W=int(sys.argv[4]) if len(sys.argv)>4 else 1600; phase=float(sys.argv[5]) if len(sys.argv)>5 else 0.0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=KM)
sc=bpy.context.scene
root=bpy.data.objects.new('turn',None); sc.collection.objects.link(root)
rng=np.random.default_rng(7)
for o in list(sc.objects):
    if o.type!='MESH': continue
    me=o.data
    bpy.context.view_layer.objects.active=o
    if me.has_custom_normals: bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for p in me.polygons: p.use_smooth=False
    # coincident surfaces shadow each other: give every unwelded face-mesh its own few-mm offset
    nv=len(me.vertices)
    if nv and len(me.edges):
        E=np.zeros(len(me.edges)*2,dtype=np.int64); me.edges.foreach_get('vertices',E); E=E.reshape(-1,2)
        n,lab=connected_components(coo_matrix((np.ones(len(E)),(E[:,0],E[:,1])),shape=(nv,nv)),directed=False)
        off=rng.uniform(-0.004,0.004,(n,3)); off[:,2]=rng.uniform(0,0.008,n)
        co=np.zeros(nv*3); me.vertices.foreach_get('co',co); me.vertices.foreach_set('co',(co.reshape(-1,3)+off[lab]).ravel()); me.update()
    o.parent=root
root.rotation_euler[2]=math.radians(ang)

def nodes(m):
    m.use_nodes=True; nt=m.node_tree; return nt,nt.nodes,nt.links,nt.nodes['Principled BSDF']
def ramp(N,L,fac,c0,c1):
    r=N.new('ShaderNodeValToRGB'); L.new(fac,r.inputs['Fac']); r.color_ramp.elements[0].color=(*c0,1); r.color_ramp.elements[1].color=(*c1,1); return r.outputs['Color']
def bump(N,L,h,b,s,d=0.01):
    bp=N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=s; bp.inputs['Distance'].default_value=d
    L.new(h,bp.inputs['Height']); L.new(bp.outputs['Normal'],b.inputs['Normal']); return bp
def objco(N):
    t=N.new('ShaderNodeTexCoord'); return t
# colours: linear RGB
def m_cmu():
    m=bpy.data.materials.new('cmu'); nt,N,L,b=nodes(m); t=objco(N)
    sep=N.new('ShaderNodeSeparateXYZ'); L.new(t.outputs['Object'],sep.inputs[0])
    # wrap blocks round the curved walls: horizontal = x+y, vertical = z (courses stay level)
    ad=N.new('ShaderNodeMath'); ad.operation='ADD'; L.new(sep.outputs[0],ad.inputs[0]); L.new(sep.outputs[1],ad.inputs[1])
    cmb=N.new('ShaderNodeCombineXYZ'); L.new(ad.outputs[0],cmb.inputs[0]); L.new(sep.outputs[2],cmb.inputs[1])
    br=N.new('ShaderNodeTexBrick'); L.new(cmb.outputs[0],br.inputs['Vector'])
    br.inputs['Scale'].default_value=1.0; br.inputs['Brick Width'].default_value=0.40; br.inputs['Row Height'].default_value=0.20
    br.inputs['Mortar Size'].default_value=0.008; br.inputs['Mortar Smooth'].default_value=0.3; br.offset=0.5
    br.inputs['Color1'].default_value=(0.060,0.057,0.053,1); br.inputs['Color2'].default_value=(0.085,0.081,0.075,1); br.inputs['Mortar'].default_value=(0.14,0.135,0.125,1)
    nz=N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value=18; L.new(t.outputs['Object'],nz.inputs['Vector'])
    mx=N.new('ShaderNodeMixRGB'); mx.blend_type='MULTIPLY'; mx.inputs[0].default_value=0.35; L.new(br.outputs['Color'],mx.inputs[1]); L.new(nz.outputs['Color'],mx.inputs[2])
    L.new(mx.outputs[0],b.inputs['Base Color']); b.inputs['Roughness'].default_value=0.9
    inv=N.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1; L.new(br.outputs['Fac'],inv.inputs[1])
    bump(N,L,inv.outputs[0],b,0.5,0.015); return m
def m_wood(name,base,plank=True,coat=0.1):
    m=bpy.data.materials.new(name); nt,N,L,b=nodes(m); t=objco(N)
    wv=N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value=3; wv.inputs['Distortion'].default_value=4; wv.inputs['Detail'].default_value=3
    L.new(t.outputs['Object'],wv.inputs['Vector'])
    grain=ramp(N,L,wv.outputs['Fac'],[x*0.88 for x in base],[x*1.1 for x in base])
    col=grain
    if plank:
        br=N.new('ShaderNodeTexBrick'); L.new(t.outputs['Object'],br.inputs['Vector'])
        br.inputs['Scale'].default_value=1.0; br.inputs['Brick Width'].default_value=2.4; br.inputs['Row Height'].default_value=0.14
        br.inputs['Mortar Size'].default_value=0.006; br.offset=0.37
        br.inputs['Color1'].default_value=(1,1,1,1); br.inputs['Color2'].default_value=(0.86,0.86,0.86,1); br.inputs['Mortar'].default_value=(0.25,0.25,0.25,1)
        mul=N.new('ShaderNodeMixRGB'); mul.blend_type='MULTIPLY'; mul.inputs[0].default_value=1.0; L.new(grain,mul.inputs[1]); L.new(br.outputs['Color'],mul.inputs[2])
        # planks only on (near-)horizontal faces
        geo=N.new('ShaderNodeNewGeometry'); sp=N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'],sp.inputs[0])
        ab=N.new('ShaderNodeMath'); ab.operation='ABSOLUTE'; L.new(sp.outputs[2],ab.inputs[0])
        gt=N.new('ShaderNodeMath'); gt.operation='GREATER_THAN'; gt.inputs[1].default_value=0.85; L.new(ab.outputs[0],gt.inputs[0])
        sel=N.new('ShaderNodeMixRGB'); L.new(gt.outputs[0],sel.inputs[0]); L.new(grain,sel.inputs[1]); L.new(mul.outputs[0],sel.inputs[2]); col=sel.outputs[0]
        inv=N.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1; L.new(br.outputs['Fac'],inv.inputs[1])
        hm=N.new('ShaderNodeMath'); hm.operation='MULTIPLY'; L.new(inv.outputs[0],hm.inputs[0]); L.new(gt.outputs[0],hm.inputs[1])
        bump(N,L,hm.outputs[0],b,0.4,0.01)
    L.new(col,b.inputs['Base Color']); b.inputs['Roughness'].default_value=0.62; b.inputs['Coat Weight'].default_value=coat; b.inputs['Coat Roughness'].default_value=0.3
    return m
def m_simple(name,base,rough,metal=0.0,noise=None,nb=0.0):
    m=bpy.data.materials.new(name); nt,N,L,b=nodes(m)
    b.inputs['Base Color'].default_value=(*base,1); b.inputs['Roughness'].default_value=rough; b.inputs['Metallic'].default_value=metal
    if noise:
        t=objco(N); nz=N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value=noise; nz.inputs['Detail'].default_value=8; L.new(t.outputs['Object'],nz.inputs['Vector'])
        L.new(ramp(N,L,nz.outputs['Fac'],[x*0.75 for x in base],[x*1.2 for x in base]),b.inputs['Base Color'])
        if nb: bump(N,L,nz.outputs['Fac'],b,nb,0.02)
    return m
def m_stones():
    m=bpy.data.materials.new('stones'); nt,N,L,b=nodes(m); t=objco(N)
    v=N.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value=22; v.feature='F1'; L.new(t.outputs['Object'],v.inputs['Vector'])
    v2=N.new('ShaderNodeTexVoronoi'); v2.inputs['Scale'].default_value=22; v2.feature='DISTANCE_TO_EDGE'; L.new(t.outputs['Object'],v2.inputs['Vector'])
    L.new(ramp(N,L,v.outputs['Color'],(0.16,0.15,0.135),(0.42,0.40,0.37)),b.inputs['Base Color'])
    pw=N.new('ShaderNodeMath'); pw.operation='POWER'; pw.inputs[1].default_value=0.4; L.new(v2.outputs['Distance'],pw.inputs[0])
    bump(N,L,pw.outputs[0],b,0.8,0.02); b.inputs['Roughness'].default_value=0.75; return m
def m_moss_roof(wood):
    m=wood.copy(); m.name='mossroof'; nt=m.node_tree; N=nt.nodes; L=nt.links; b=N['Principled BSDF']
    t=N.new('ShaderNodeTexCoord'); g=N.new('ShaderNodeVectorMath'); g.operation='SUBTRACT'; g.inputs[1].default_value=(0.5,0.5,0.5); L.new(t.outputs['Generated'],g.inputs[0])
    sx=N.new('ShaderNodeVectorMath'); sx.operation='MULTIPLY'; sx.inputs[1].default_value=(2,2,0); L.new(g.outputs[0],sx.inputs[0])
    ln=N.new('ShaderNodeVectorMath'); ln.operation='LENGTH'; L.new(sx.outputs[0],ln.inputs[0])
    nz=N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value=6; L.new(t.outputs['Object'],nz.inputs['Vector'])
    ed=N.new('ShaderNodeMath'); ed.operation='MULTIPLY_ADD'; L.new(nz.outputs['Fac'],ed.inputs[0]); ed.inputs[1].default_value=0.12; L.new(ln.outputs['Value'],ed.inputs[2])
    mask=N.new('ShaderNodeMath'); mask.operation='LESS_THAN'; mask.inputs[1].default_value=0.68; L.new(ed.outputs[0],mask.inputs[0])
    # only the upward face carries moss
    geo=N.new('ShaderNodeNewGeometry'); sp=N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'],sp.inputs[0])
    up=N.new('ShaderNodeMath'); up.operation='GREATER_THAN'; up.inputs[1].default_value=0.5; L.new(sp.outputs[2],up.inputs[0])
    mk=N.new('ShaderNodeMath'); mk.operation='MULTIPLY'; L.new(mask.outputs[0],mk.inputs[0]); L.new(up.outputs[0],mk.inputs[1])
    mn=N.new('ShaderNodeTexNoise'); mn.inputs['Scale'].default_value=40; mn.inputs['Detail'].default_value=10; L.new(t.outputs['Object'],mn.inputs['Vector'])
    moss=N.new('ShaderNodeBsdfPrincipled'); moss.inputs['Roughness'].default_value=1.0
    L.new(ramp(N,L,mn.outputs['Fac'],(0.030,0.045,0.012),(0.11,0.15,0.04)),moss.inputs['Base Color'])
    bp=N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=1.0; bp.inputs['Distance'].default_value=0.03; L.new(mn.outputs['Fac'],bp.inputs['Height']); L.new(bp.outputs['Normal'],moss.inputs['Normal'])
    mix=N.new('ShaderNodeMixShader'); L.new(mk.outputs[0],mix.inputs[0]); L.new(b.outputs[0],mix.inputs[1]); L.new(moss.outputs[0],mix.inputs[2])
    L.new(mix.outputs[0],N['Material Output'].inputs['Surface']); return m
def m_glass():
    m=bpy.data.materials.new('glass'); nt,N,L,b=nodes(m)
    b.inputs['Base Color'].default_value=(0.93,0.96,0.95,1); b.inputs['Transmission Weight'].default_value=1.0
    b.inputs['Roughness'].default_value=0.0; b.inputs['IOR'].default_value=1.5; return m
def m_fire():
    m=bpy.data.materials.new('fire'); nt=m.node_tree if m.use_nodes else None; m.use_nodes=True; nt=m.node_tree; N=nt.nodes; L=nt.links; N.clear()
    o=N.new('ShaderNodeOutputMaterial'); vol=N.new('ShaderNodeVolumePrincipled'); L.new(vol.outputs[0],o.inputs['Volume'])
    t=N.new('ShaderNodeTexCoord')
    # flame: dense, bright at the base, thinning upward, broken up by rising noise
    sep=N.new('ShaderNodeSeparateXYZ'); L.new(t.outputs['Generated'],sep.inputs[0])
    hz=N.new('ShaderNodeMath'); hz.operation='SUBTRACT'; hz.inputs[0].default_value=1; L.new(sep.outputs[2],hz.inputs[1])
    cx=N.new('ShaderNodeVectorMath'); cx.operation='SUBTRACT'; cx.inputs[1].default_value=(0.5,0.5,0); L.new(t.outputs['Generated'],cx.inputs[0])
    cm=N.new('ShaderNodeVectorMath'); cm.operation='MULTIPLY'; cm.inputs[1].default_value=(1,1,0); L.new(cx.outputs[0],cm.inputs[0])
    rr=N.new('ShaderNodeVectorMath'); rr.operation='LENGTH'; L.new(cm.outputs[0],rr.inputs[0])
    lim=N.new('ShaderNodeMath'); lim.operation='MULTIPLY'; lim.inputs[1].default_value=0.55; L.new(hz.outputs[0],lim.inputs[0])
    inside=N.new('ShaderNodeMath'); inside.operation='SUBTRACT'; L.new(lim.outputs[0],inside.inputs[0]); L.new(rr.outputs['Value'],inside.inputs[1])
    nz=N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value=3.5; nz.inputs['Detail'].default_value=6; nz.noise_dimensions='4D'; nz.inputs['W'].default_value=phase*4
    mp=N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value=(1,1,0.45); L.new(t.outputs['Object'],mp.inputs['Vector']); L.new(mp.outputs[0],nz.inputs['Vector'])
    sh=N.new('ShaderNodeMath'); sh.operation='MULTIPLY_ADD'; L.new(nz.outputs['Fac'],sh.inputs[0]); sh.inputs[1].default_value=0.35; L.new(inside.outputs[0],sh.inputs[2])
    d=N.new('ShaderNodeMath'); d.operation='SUBTRACT'; L.new(sh.outputs[0],d.inputs[0]); d.inputs[1].default_value=0.2
    cl=N.new('ShaderNodeMath'); cl.operation='MULTIPLY'; cl.use_clamp=True; L.new(d.outputs[0],cl.inputs[0]); cl.inputs[1].default_value=6
    vol.inputs['Density'].default_value=0.0
    L.new(cl.outputs[0],vol.inputs['Emission Strength'])
    em=N.new('ShaderNodeMath'); em.operation='MULTIPLY'; L.new(cl.outputs[0],em.inputs[0]); em.inputs[1].default_value=60; L.new(em.outputs[0],vol.inputs['Emission Strength'])
    bb=N.new('ShaderNodeValToRGB'); L.new(hz.outputs[0],bb.inputs['Fac'])
    bb.color_ramp.elements[0].color=(1.0,0.12,0.01,1); bb.color_ramp.elements[1].color=(1.0,0.55,0.12,1)
    L.new(bb.outputs['Color'],vol.inputs['Emission Color']); return m

wood=m_wood('timber',(0.20,0.15,0.105))
M={'masonry':m_cmu(),'timber':wood,'glulam':m_wood('glulam',(0.36,0.25,0.15),plank=False,coat=0.25),
   'plinth':m_stones(),'chimney':m_simple('corten',(0.20,0.075,0.03),0.55,metal=0.6,noise=7,nb=0.15),
   'metal':m_simple('metal',(0.04,0.04,0.04),0.4,metal=0.9),'figures':m_simple('figures',(0.70,0.68,0.65),0.65),
   'glass':m_glass()}
SPECIAL={'timber#701':m_moss_roof(wood),'timber#1546':M['chimney'],'masonry#630':M['masonry']}
for o in sc.objects:
    if o.type!='MESH': continue
    k=o.name.split('#')[0]
    o.data.materials[0]=SPECIAL.get(o.name,M.get(k,M['timber']))
# ground ring slabs low to the ground read as the beach-stone ambulatory; the huge site slabs stay neutral
for nm in ('plinth#1581','plinth#1583'):
    if nm in sc.objects: sc.objects[nm].data.materials[0]=m_simple('site',(0.30,0.29,0.275),0.95,noise=3)

def world_to_local(p): return mathutils.Vector(p)
def add_fire(name,center,radius,height,watts):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=radius,depth=height,location=(center[0],center[1],center[2]+height/2))
    f=bpy.context.object; f.name=name; f.data.materials.append(m_fire()); f.parent=root
    f.visible_shadow=False
    li=bpy.data.lights.new(name+'L','POINT'); li.energy=watts; li.color=(1.0,0.5,0.18); li.shadow_soft_size=radius*0.8
    lo=bpy.data.objects.new(name+'L',li); lo.visible_camera=False; sc.collection.objects.link(lo); lo.location=(center[0],center[1],center[2]+height*0.35); lo.parent=root
    # embers / logs
    for i in range(5):
        a=i*2*math.pi/5+0.3
        bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=radius*0.09,depth=radius*1.3,location=(center[0]+math.cos(a)*radius*0.15,center[1]+math.sin(a)*radius*0.15,center[2]+radius*0.08),rotation=(math.pi/2,0,a))
        lg=bpy.context.object; lg.parent=root
        lm=bpy.data.materials.new('log'); lm.use_nodes=True; pb=lm.node_tree.nodes['Principled BSDF']; pb.inputs['Base Color'].default_value=(0.02,0.015,0.01,1); pb.inputs['Roughness'].default_value=0.9
        pb.inputs['Emission Color'].default_value=(1,0.25,0.03,1); pb.inputs['Emission Strength'].default_value=0.6; lg.data.materials.append(lm)
# Fire Core bowl (outdoor gathering space) and the hearth under the chimney
add_fire('firecore',(-0.94,6.47,0.40),0.42,1.0,900)
add_fire('hearth',(3.23,1.34,0.24),0.38,0.9,600)
# warm interior light so the glazing glows at dusk instead of reading black
for nm,(x,y,z),wv in (('yoga',(1.0,-5.7,2.4),1400),('yoga2',(-1.5,-3.5,2.2),600),('house',(-4.0,2.5,2.0),700),('house2',(1.0,3.0,2.0),500)):
    li=bpy.data.lights.new(nm,'POINT'); li.energy=wv; li.color=(1.0,0.72,0.45); li.shadow_soft_size=0.6
    lo=bpy.data.objects.new(nm,li); sc.collection.objects.link(lo); lo.location=(x,y,z); lo.parent=root; lo.visible_camera=False; lo.visible_glossy=False

# studio floor and sunset sky
bpy.ops.mesh.primitive_plane_add(size=600,location=(0,0,-0.003))
fl=bpy.context.object; fl.data.materials.append(m_simple('floor',(0.42,0.42,0.42),0.95))
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; WN=w.node_tree.nodes; WL=w.node_tree.links
WN['Background'].inputs['Color'].default_value=(0.30,0.34,0.50,1); WN['Background'].inputs['Strength'].default_value=0.5
sun=bpy.data.lights.new('sun','SUN'); sun.energy=4.2; sun.angle=math.radians(1.2); sun.color=(1.0,0.66,0.42)
so=bpy.data.objects.new('sun',sun); sc.collection.objects.link(so); so.rotation_euler=(math.radians(90-11),0,math.radians(78))

cam=bpy.data.cameras.new('cam'); cam.lens=50; co=bpy.data.objects.new('cam',cam); sc.collection.objects.link(co); sc.camera=co
tgt=mathutils.Vector((0,0,1.6)); dist=58; th=math.radians(35); ph=math.radians(58)
co.location=tgt+mathutils.Vector((dist*math.sin(ph)*math.sin(th),-dist*math.sin(ph)*math.cos(th),dist*math.cos(ph)))
co.rotation_euler=(tgt-co.location).to_track_quat('-Z','Y').to_euler()
r=sc.render; r.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=spp; sc.cycles.use_denoising=True; sc.cycles.use_adaptive_sampling=True
sc.cycles.max_bounces=8; sc.cycles.transmission_bounces=8; sc.cycles.volume_bounces=0; sc.cycles.caustics_reflective=False; sc.cycles.caustics_refractive=False
sc.cycles.volume_step_rate=2.0
r.resolution_x=W; r.resolution_y=int(W*10/16)
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=0.2
r.filepath=out; r.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
