"""Kodolu Maja turntable scene. Usage: python scene.py OUT.png [angle_deg] [samples] [width]"""
import bpy, math, sys, mathutils
KM='/tmp/claude-0/-home-claude/4f37e95d-919e-58a9-8612-3aeead9a426c/scratchpad/km/km5.glb'
out=sys.argv[1]; ang=float(sys.argv[2]) if len(sys.argv)>2 else 0; spp=int(sys.argv[3]) if len(sys.argv)>3 else 64
W=int(sys.argv[4]) if len(sys.argv)>4 else 1600
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=KM)
sc=bpy.context.scene
import bmesh
for o in list(sc.objects):
    if o.type!='MESH': continue
    bm=bmesh.new(); bm.from_mesh(o.data)
    seen=set(); kill=[]
    for f in bm.faces:  # stacked duplicate faces shadow each other into black streaks
        c=f.calc_center_median(); k=(round(c.x,2),round(c.y,2),round(c.z,2))
        if k in seen: kill.append(f)
        else: seen.add(k)
    bmesh.ops.delete(bm,geom=kill,context='FACES')
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    bpy.context.view_layer.objects.active=o
    if o.data.has_custom_normals: bpy.ops.mesh.customdata_custom_splitnormals_clear()
    # separate coincident surfaces: shift each connected piece by its own few millimetres
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    me=o.data; nv=len(me.vertices)
    if nv and len(me.edges):
        E=np.zeros(len(me.edges)*2,dtype=np.int64); me.edges.foreach_get('vertices',E); E=E.reshape(-1,2)
        g=coo_matrix((np.ones(len(E)),(E[:,0],E[:,1])),shape=(nv,nv))
        n,lab=connected_components(g,directed=False)
        rng=np.random.default_rng(len(o.name)); off=rng.uniform(-0.004,0.004,(n,3)); off[:,2]=rng.uniform(0.0,0.008,n)
        co=np.zeros(nv*3); me.vertices.foreach_get('co',co); co=co.reshape(-1,3)+off[lab]; me.vertices.foreach_set('co',co.ravel()); me.update()
        print(o.name,'pieces',n)
root=bpy.data.objects.new('turn',None); sc.collection.objects.link(root)
for o in list(sc.objects):
    if o.type=='MESH':
        o.parent=root
        for p in o.data.polygons: p.use_smooth=False
        o.cycles.shadow_terminator_geometry_offset=0.1
        # sharp edges keep crisp facets, curved walls stay smooth
        mod=o.modifiers.new('ws','WEIGHTED_NORMAL') if False else None
root.rotation_euler[2]=math.radians(ang)

def mat(name,base,rough,metal=0.0,noise=None,bump=0.0,wave=None,trans=0.0,ior=1.45,coat=0.0,spec=0.5):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; N=nt.nodes; L=nt.links
    b=N['Principled BSDF']; b.inputs['Roughness'].default_value=rough; b.inputs['Metallic'].default_value=metal
    b.inputs['Base Color'].default_value=(*base,1); b.inputs['Specular IOR Level'].default_value=spec
    if trans:
        b.inputs['Transmission Weight'].default_value=trans; b.inputs['IOR'].default_value=ior
    if coat: b.inputs['Coat Weight'].default_value=coat; b.inputs['Coat Roughness'].default_value=0.2
    tc=N.new('ShaderNodeTexCoord')
    col=None
    if noise or wave:
        if wave:
            t=N.new('ShaderNodeTexWave'); t.wave_type='BANDS'; t.bands_direction='Z' if wave.get('dir')=='Z' else 'X'
            t.inputs['Scale'].default_value=wave['scale']; t.inputs['Distortion'].default_value=wave.get('dist',6)
            t.inputs['Detail'].default_value=3
        else:
            t=N.new('ShaderNodeTexNoise'); t.inputs['Scale'].default_value=noise; t.inputs['Detail'].default_value=8; t.inputs['Roughness'].default_value=0.6
        L.new(tc.outputs['Object'],t.inputs['Vector'])
        r=N.new('ShaderNodeValToRGB'); L.new(t.outputs['Fac'],r.inputs['Fac'])
        k=0.12 if wave else 0.22
        dk=[x*(1-k) for x in base]; lt=[min(1,x*(1+k)) for x in base]
        r.color_ramp.elements[0].color=(*dk,1); r.color_ramp.elements[1].color=(*lt,1)
        L.new(r.outputs['Color'],b.inputs['Base Color'])
        rr=N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value=rough-0.12; rr.inputs['To Max'].default_value=min(1,rough+0.12)
        L.new(t.outputs['Fac'],rr.inputs['Value']); L.new(rr.outputs['Result'],b.inputs['Roughness'])
        if bump:
            bp=N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=bump; bp.inputs['Distance'].default_value=0.02
            L.new(t.outputs['Fac'],bp.inputs['Height']); L.new(bp.outputs['Normal'],b.inputs['Normal'])
    return m
# colours in linear RGB
M={
 'masonry':mat('masonry',(0.042,0.038,0.034),0.82,noise=2.5,bump=0.25),
 'timber': mat('timber',(0.22,0.165,0.115),0.6,wave={'scale':1.6,'dist':3},bump=0.06,coat=0.15),
 'glulam': mat('glulam',(0.30,0.225,0.155),0.55,wave={'scale':2.2,'dist':5,'dir':'Z'},bump=0.04,coat=0.2),
 'plinth': mat('plinth',(0.36,0.345,0.32),0.9,noise=6,bump=0.12),
 'chimney':mat('chimney',(0.28,0.15,0.09),0.38,metal=0.85,noise=4,bump=0.05),
 'metal':  mat('metal',(0.05,0.05,0.048),0.35,metal=0.9),
 'figures':mat('figures',(0.72,0.70,0.67),0.65),
 'glass':  mat('glass',(0.92,0.96,0.95),0.02,trans=1.0),
}
for o in sc.objects:
    if o.type=='MESH' and o.name in M: o.data.materials[0]=M[o.name]

# studio floor + cyclorama tone
bpy.ops.mesh.primitive_plane_add(size=400,location=(0,0,-0.002))
fl=bpy.context.object; fm=mat('floor',(0.46,0.445,0.425),0.95); fl.data.materials.append(fm)
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True
bg=w.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(0.46,0.445,0.425,1); bg.inputs['Strength'].default_value=0.8
# key: soft late-afternoon sun from front-left; fill comes from the world
sun=bpy.data.lights.new('sun','SUN'); sun.energy=3.2; sun.angle=math.radians(4); sun.color=(1.0,0.93,0.84)
so=bpy.data.objects.new('sun',sun); sc.collection.objects.link(so)
so.rotation_euler=(math.radians(52),0,math.radians(-35))

# camera: matches the page view (35deg around, 60deg down from vertical)
cam=bpy.data.cameras.new('cam'); cam.lens=50; co=bpy.data.objects.new('cam',cam); sc.collection.objects.link(co); sc.camera=co
tgt=mathutils.Vector((0,0,1.6)); dist=58; th=math.radians(35); ph=math.radians(58)
co.location=tgt+mathutils.Vector((dist*math.sin(ph)*math.sin(th),-dist*math.sin(ph)*math.cos(th),dist*math.cos(ph)))
co.rotation_euler=(tgt-co.location).to_track_quat('-Z','Y').to_euler()

r=sc.render; r.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=spp; sc.cycles.use_denoising=True
sc.cycles.max_bounces=8; sc.cycles.transmission_bounces=8; sc.cycles.caustics_reflective=False; sc.cycles.caustics_refractive=False
sc.cycles.use_adaptive_sampling=True
r.resolution_x=W; r.resolution_y=int(W*10/16); r.film_transparent=False
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'
r.filepath=out; r.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
