import sys, rhino3dm, numpy as np, trimesh, io
from PIL import Image, ImageFilter
m=rhino3dm.File3dm.Read(sys.argv[1]); out=sys.argv[2]
def to_np(rm):
    v=np.array([[p.X,p.Y,p.Z] for p in rm.Vertices],dtype=np.float64); f=[]
    for i in range(len(rm.Faces)):
        a=rm.Faces[i]
        if len(a)==4 and a[2]!=a[3]: f+=[[a[0],a[1],a[2]],[a[0],a[2],a[3]]]
        else: f.append([a[0],a[1],a[2]])
    return (v,np.array(f,dtype=np.int64)) if f else None
def meshes(g):
    if isinstance(g,rhino3dm.Mesh): return [g]
    if isinstance(g,rhino3dm.Extrusion):
        mm=g.GetMesh(rhino3dm.MeshType.Any); return [mm] if mm else []
    if isinstance(g,rhino3dm.Brep): return [x for x in (fc.GetMesh(rhino3dm.MeshType.Any) for fc in g.Faces) if x]
    return []
def ruled_ramp(g,sides=(2,4),n=240,k=6):
    """Rebuild the sloped top and bottom of a helical ramp slab whose own trimmed faces mesh badly:
    a ramp is a ruled surface between the matching edges of its two untrimmed curved sides."""
    edges=[]
    for fi in sides:
        f=g.Faces[fi]; d0,d1=f.Domain(0),f.Domain(1)
        P=lambda u,v:(lambda p:(p.X,p.Y,p.Z))(f.PointAt(u,v))
        L0=sum(np.linalg.norm(np.subtract(P(d0.T0+(d0.T1-d0.T0)*i/8,d1.T0),P(d0.T0+(d0.T1-d0.T0)*(i+1)/8,d1.T0))) for i in range(8))
        L1=sum(np.linalg.norm(np.subtract(P(d0.T0,d1.T0+(d1.T1-d1.T0)*i/8),P(d0.T0,d1.T0+(d1.T1-d1.T0)*(i+1)/8))) for i in range(8))
        if L0>=L1: a=[np.array([P(u,d1.T0) for u in np.linspace(d0.T0,d0.T1,n)]),np.array([P(u,d1.T1) for u in np.linspace(d0.T0,d0.T1,n)])]
        else: a=[np.array([P(d0.T0,v) for v in np.linspace(d1.T0,d1.T1,n)]),np.array([P(d0.T1,v) for v in np.linspace(d1.T0,d1.T1,n)])]
        a.sort(key=lambda c:c[:,2].mean()); edges.append(a)  # [bottom, top]
    out=[]
    for lvl in (0,1):
        A=edges[0][lvl]; B=edges[1][lvl]
        if np.linalg.norm(A[0]-B[0])>np.linalg.norm(A[0]-B[-1]): B=B[::-1]
        V=np.concatenate([A+(B-A)*t for t in np.linspace(0,1,k)]); F=[]
        for j in range(k-1):
            for i in range(n-1):
                a,b,c,d=j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i; F+=[[a,b,c],[a,c,d]]
        out.append((V,np.array(F)))
    return out
REBUILD={1502:((0,5),(2,4)),1508:((0,5),(2,4))}  # object index: (bad faces to drop, untrimmed sides to rule between)
seen=set()
def is_glass(a): return str(a.ColorSource).endswith('ColorFromObject') and tuple(a.ObjectColor)[3]<255 and tuple(a.ObjectColor)[:3]==(184,242,240)
objs=[]
def collect(L,g,attr,xf=None,idx=None):
    parts=[]
    ms=meshes(g)
    if idx in REBUILD:
        drop,sides=REBUILD[idx]
        ms=[fc.GetMesh(rhino3dm.MeshType.Any) for j,fc in enumerate(g.Faces) if j not in drop]
        for v,f in ruled_ramp(g,sides): parts.append(trimesh.Trimesh(v,f,process=False))
    # the model holds some objects twice; stacked copies render as black streaks
    sig=tuple(np.round(np.concatenate([to_np(x)[0] for x in ms if x and to_np(x)]).sum(0),2)) if ms else None
    if sig is not None and xf is None:
        if (L,sig) in seen: return
        seen.add((L,sig))
    for rm in ms:
        r=to_np(rm)
        if r is None: continue
        v,f=r
        if xf is not None: v=(np.c_[v,np.ones(len(v))]@np.array(xf).T)[:,:3]
        parts.append(trimesh.Trimesh(v,f,process=False))
    if parts: objs.append((L,attr,trimesh.util.concatenate(parts),idx))
for oi,o in enumerate(m.Objects):
    L=m.Layers[o.Attributes.LayerIndex].FullPath
    if L.startswith('Make2D') or L=='PLAN': continue
    g=o.Geometry
    if isinstance(g,rhino3dm.InstanceReference):
        d=m.InstanceDefinitions.FindId(g.ParentIdefId); X=g.Xform
        xf=[[X.M00,X.M01,X.M02,X.M03],[X.M10,X.M11,X.M12,X.M13],[X.M20,X.M21,X.M22,X.M23],[X.M30,X.M31,X.M32,X.M33]]
        for gid in d.GetObjectIds():
            ob=m.Objects.FindId(gid)
            if ob is not None: collect(L,ob.Geometry,ob.Attributes,xf)
    else: collect(L,g,o.Attributes,idx=oi)
zmin=min(t.bounds[0][2] for _,_,t,_ in objs)
import os
SPLIT=os.environ.get('SPLIT')
groups={}
for L,a,t,oi in objs:
    (x0,y0,z0),(x1,y1,z1)=t.bounds
    if is_glass(a): k='glass'
    elif L=='OLD':
        k='chimney' if (x1-x0)<5 and (y1-y0)<5 and (z1-z0)>8 else 'masonry'
    elif L=='0': k='plinth' if z1-zmin<1.5 else 'timber'
    elif L=='STAIRSA': k='timber'
    elif L=='WOOD': k='glulam'
    elif L=='METAL': k='metal'
    elif L=='YOGA': k='figures'
    else: k='timber'
    groups.setdefault(f'{k}#{oi}' if SPLIT else k,[]).append(t)
MAT={ # desaturated palette taken from the renderings
 'masonry':((56,53,50),0.0,0.92),'timber':((124,96,70),0.0,0.78),'glulam':((150,114,78),0.0,0.7),
 'plinth':((150,146,139),0.0,0.95),'chimney':((122,86,66),0.45,0.55),'metal':((58,56,54),0.7,0.45),
 'figures':((196,190,182),0.0,0.9)}
scene=trimesh.Scene()
for k,ts in groups.items():
    mm=trimesh.util.concatenate(ts)
    kk=k; k=k.split('#')[0]
    if k=='glass':
        mat=trimesh.visual.material.PBRMaterial(baseColorFactor=[0.93,0.95,0.94,0.16],metallicFactor=0.0,roughnessFactor=0.06,alphaMode='BLEND',doubleSided=True)
    else:
        c,me,ro=MAT[k]
        mat=trimesh.visual.material.PBRMaterial(baseColorFactor=[c[0]/255,c[1]/255,c[2]/255,1.0],metallicFactor=me,roughnessFactor=ro,doubleSided=True)
    mm.visual=trimesh.visual.TextureVisuals(material=mat); scene.add_geometry(mm,geom_name=kk)
    if not SPLIT: print(k,len(ts),len(mm.faces))
T=np.eye(4); T[:3,:3]*=0.3048
scene.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0])@T)
b=scene.bounds; c=(b[0]+b[1])/2
scene.apply_translation([-c[0],-b[0][1],-c[2]])
ext=scene.extents; R=max(ext[0],ext[2])*0.8
if '--ground' in sys.argv:
    # grassy earth ground: baked texture with radial fade to transparent
    N=1024; rng=np.random.default_rng(7)
    def noise(scale):
        a=rng.random((N//scale+2,N//scale+2)).astype(np.float32)
        im=Image.fromarray((a*255).astype(np.uint8)).resize((N,N),Image.BICUBIC).filter(ImageFilter.GaussianBlur(scale/3))
        return np.asarray(im,dtype=np.float32)/255
    n=0.45*noise(64)+0.3*noise(16)+0.15*noise(4)+0.1*rng.random((N,N))
    grass=np.array([92,98,76],dtype=np.float32); earth=np.array([112,100,82],dtype=np.float32); dark=np.array([66,70,56],dtype=np.float32)
    patch=np.clip((noise(48)-0.45)*3,0,1)[...,None]
    col=grass*(1-patch)+earth*patch
    col=col*(0.82+0.36*n[...,None])
    col=col*(1-0.25*np.clip(noise(8)-0.5,0,1)[...,None]*2)+0*dark
    yy,xx=np.mgrid[0:N,0:N]; r=np.hypot(xx-N/2,yy-N/2)/(N/2)
    fall=np.clip((1-r)/0.5,0,1)**1.3
    alpha=(fall>(0.15+0.7*rng.random((N,N))*0.6+0.35*noise(6))).astype(np.float32)
    rgba=np.dstack([np.clip(col,0,255),alpha*255]).astype(np.uint8)
    tex=Image.fromarray(rgba,'RGBA')
    ground=trimesh.creation.cylinder(radius=R,height=0.01,sections=96)
    ground.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]))
    ground.apply_translation([0,-0.03,0])
    v=ground.vertices; uv=np.c_[(v[:,0]/R+1)/2,(v[:,2]/R+1)/2]
    gm=trimesh.visual.material.PBRMaterial(baseColorTexture=tex,baseColorFactor=[255,255,255,255],metallicFactor=0,roughnessFactor=1,alphaMode='MASK',alphaCutoff=0.5,doubleSided=True)
    ground.visual=trimesh.visual.TextureVisuals(uv=uv,material=gm)
    scene.add_geometry(ground,geom_name='ground')
scene.export(out); print('R',R)
