"""Evaluate v2 outputs on real photos: orientation, geometry, crop coverage of the music (ink) box."""
import sys, csv, json, os, numpy as np, cv2
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from make_oracle import P, print_box, paper_quad
from eval_v2_geometry import sim_fit
ink=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inkbox.json')))
def run(diag, report, outdir):
    rows=list(csv.DictReader(open(diag,encoding='utf-8'))); box=print_box(rows); D={r['file']:r for r in rows}
    res=[]
    for r in csv.DictReader(open(report,encoding='utf-8')):
        d=D[r['file']]; cond=r['file'].split('__')[1].rsplit('_',1)[0]
        row=dict(file=r['file'],cond=cond,method=r['method'].split(':')[0])
        if r['H'] and d.get('oracle_quad'):
            H=np.array([float(v) for v in r['H'].split(';')]).reshape(3,3)
            q=P(d['oracle_quad']).astype(np.float64)*(float(os.environ.get('INLONG',0))/max(float(d['W']),float(d['H'])) if os.environ.get('INLONG') else 1.0)
            pq=paper_quad(q.astype(np.float32),box).astype(np.float64)
            e,rot=sim_fit(cv2.perspectiveTransform(pq.reshape(-1,1,2),H).reshape(4,2))
            # ink box in ref-normalised coords -> photo via quad homography -> output
            A=cv2.getPerspectiveTransform(np.float32([[0,0],[1,0],[1,1],[0,1]]),q.astype(np.float32))
            x0,y0,x1,y1=ink[r['file'].split('__')[0]]
            ib=cv2.perspectiveTransform(np.float64([[x0,y0],[x1,y0],[x1,y1],[x0,y1]]).reshape(-1,1,2),A.astype(np.float64))
            ib=cv2.perspectiveTransform(ib,H).reshape(4,2)
            im=cv2.imread(os.path.join(outdir,'raw',r['file']),cv2.IMREAD_GRAYSCALE) if outdir else None
            if im is None: continue
            h,w=im.shape; s=400/max(h,w); off=np.array([w,h])*s
            big=(int(h*s)*3,int(w*s)*3)
            m1=np.zeros(big,np.uint8); cv2.fillPoly(m1,[np.round(ib*s+off).astype(np.int32)],1)
            fr=np.zeros(big,np.uint8); fr[int(off[1]):int(off[1])+int(h*s),int(off[0]):int(off[0])+int(w*s)]=1
            m2=np.zeros(big,np.uint8); cv2.fillPoly(m2,[np.round(cv2.perspectiveTransform(pq.reshape(-1,1,2),H).reshape(4,2)*s+off).astype(np.int32)],1)
            cover=(m1&fr).sum()/max(1,m1.sum()); pagefrac=(m2&fr).sum()/max(1,fr.sum())
            row.update(orient_ok=int(abs(rot)<45),geo_err=round(e,4),cover=round(float(cover),3),pagefrac=round(float(pagefrac),3))
        else:
            row.update(orient_ok=np.nan)
        res.append(row)
    return res
if __name__=='__main__':
    import collections
    rows=run(sys.argv[1],sys.argv[2],sys.argv[3])
    keys=[]
    for r in rows: keys+=[k for k in r if k not in keys]
    with open(sys.argv[4],'w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=keys); w.writeheader(); w.writerows(rows)
    by=collections.defaultdict(list)
    for r in rows: by[r['cond']].append(r)
    print(f"{'Điều kiện':10s} {'n':>3s} {'đúng hướng':>10s} {'hình học<2%':>11s} {'giữ>=97% nhạc':>13s} {'tốt cả 3':>8s}")
    for c in sorted(by):
        xs=by[c]; ok=lambda r,k,f: (k in r and r[k]==r[k] and f(r[k]))
        o=sum(ok(r,'orient_ok',lambda v:v==1) for r in xs); g=sum(ok(r,'geo_err',lambda v:v<0.02) for r in xs)
        cv=sum(ok(r,'cover',lambda v:v>0.97) for r in xs)
        good=sum(ok(r,'orient_ok',lambda v:v==1) and ok(r,'geo_err',lambda v:v<0.02) and ok(r,'cover',lambda v:v>0.97) for r in xs)
        print(f"{c:10s} {len(xs):3d} {o:10d} {g:11d} {cv:13d} {good:8d}")
