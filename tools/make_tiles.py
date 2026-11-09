import sys
from PIL import Image, ImageDraw
# slug: (file, subject box as fractions x0,y0,x1,y1, pad) — the box is what must stay in frame.
# The frame grows around the box to 4:3 using the image itself; only where the image runs out
# and pad=True (flat backgrounds) is the edge extended with the background colour.
PICK={
 'an-unfamiliar-path':('03.jpg',(0.04,0.02,0.96,0.8),'shrink'),
 'eclipse':('02.jpg',(0.61,0.0,0.99,0.31),'shrink'),
 'fashion-explorations':('02.jpg',(0,0,1,0.75),'grow'),
 'reveal':('04.jpg',(0,0,1,1),'grow'),
 'hand-drawings':('02.jpg',(0.05,0.25,0.95,0.92),'grow'),
 'kodolu-maja':('04.jpg',(0.0,0.36,1.0,1.0),'shrink'),
 'monument-for-mars':('04.jpg',(0.27,0.12,0.97,0.96),'grow'),
 'kayak-center':('09.jpg',(0,0,1,1),'grow'),
 'studio-roma':('02.jpg',(0.0,0.31,1.0,0.36),'grow'),
 'explorations-roma':('03.png',(0.02,0,0.93,0.93),'pad'),
 'concrete-based-membranes':('02.jpg',(0.03,0.1,0.46,0.92),'shrink'),
 'light-weight-tension-structures':('03.jpg',(0.055,0.53,0.46,0.98),'shrink'),
 'high-performance-building':('02.jpg',(0.03,0.35,0.95,0.9),'shrink'),
 'the-dude-series':('03.jpg',(0,0.25,1,1),'grow'),
 'media-city':('02.jpg',(0.34,0.25,0.9,0.75),'shrink'),
 'bamboo-tension-bridge':('02.jpg',(0.08,0.08,0.97,0.225),'shrink'),
 'fractura':('06.jpg',(0,0,1,1),'grow'),
 'ncma':('03.jpg',(0,0,1,1),'pad'),
 'graphic-designs':('03.jpg',(0,0,1,1),'grow'),
 'portfolio-2023':('02.jpg',(0.14,0.12,0.91,0.85),'shrink'),
}
R=4/3
def fit(im,box,mode):
    W,H=im.size; x0,y0,x1,y1=box[0]*W,box[1]*H,box[2]*W,box[3]*H
    if mode in('shrink','pad'): im=im.crop((round(x0),round(y0),round(x1),round(y1))); W,H=im.size; x0,y0,x1,y1=0,0,W,H
    w,h=x1-x0,y1-y0; cx,cy=(x0+x1)/2,(y0+y1)/2
    if mode=='pad':
        w,h=(w,w/R) if w/h>R else (h*R,h)
        can=Image.new('RGB',(round(w),round(h)),im.getpixel((6,H//2))); can.paste(im,(round((w-W)/2),round((h-H)/2))); return can
    if mode=='grow': w,h=(w,w/R) if w/h>R else (h*R,h)
    else: w,h=(h*R,h) if w/h>R else (w,w/R)
    s=min(1,W/w,H/h); w,h=w*s,h*s
    L=min(max(cx-w/2,0),W-w); T=min(max(cy-h/2,0),H-h)
    return im.crop((round(L),round(T),round(L+w),round(T+h)))
out=[]
for s,(f,box,mode) in PICK.items():
    im=Image.open(f'images/{s}/{f}').convert('RGB'); t=fit(im,box,mode)
    if t.width>1200: t=t.resize((1200,900),Image.LANCZOS)
    t.save(f'images/{s}/tile.jpg',quality=85,optimize=True,progressive=True); out.append((s,t.size))
TW,TH=240,180
sheet=Image.new('RGB',(5*(TW+8),4*(TH+22)),'white'); d=ImageDraw.Draw(sheet)
for i,(s,sz) in enumerate(out):
    im=Image.open(f'images/{s}/tile.jpg').resize((TW,TH)); x=(i%5)*(TW+8); y=(i//5)*(TH+22); sheet.paste(im,(x,y)); d.text((x,y+TH+4),f'{s[:28]} {sz[0]}x{sz[1]}',fill='black')
sheet.save(sys.argv[1],quality=85)
