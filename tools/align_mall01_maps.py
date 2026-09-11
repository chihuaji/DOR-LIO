#!/usr/bin/env python3
"""Optional rigid display registration; never use these scores as evaluation metrics."""
import numpy as np,json
from scipy.spatial import cKDTree
from pathlib import Path
from prepare_mall01_maps import SOURCES, ROOT, sample_pcd

def thin(p,v=.35):
 _,idx=np.unique(np.floor(p/v).astype('i4'),axis=0,return_index=True);return p[idx]
ref=thin(sample_pcd(SOURCES['ours'], cap=200000)[0]);ref=ref[np.all(np.isfinite(ref),axis=1)]
tree=cKDTree(ref);_,er=np.linalg.eigh(np.cov(ref.T));cr=np.median(ref,axis=0)
trans={}
for name in ['fastlio2','btsa']:
 src=thin(sample_pcd(SOURCES[name], cap=200000)[0]);_,es=np.linalg.eigh(np.cov(src.T));cs=np.median(src,axis=0)
 candidates=[]
 for signs in [(1,1,1),(1,-1,-1),(-1,1,-1),(-1,-1,1),(-1,-1,-1),(-1,1,1),(1,-1,1),(1,1,-1)]:
  r=er@np.diag(signs)@es.T
  if np.linalg.det(r)<0:continue
  for t in [np.zeros(3),cr-cs@r.T]:
   d,_=tree.query(src[::3]@r.T+t,workers=1);candidates.append((np.median(d),r,t))
 _,r,t=min(candidates,key=lambda a:a[0]);print(name,'initial',min(c[0] for c in candidates),flush=True)
 for threshold in [3,1.5,.7,.35]:
  for it in range(20):
   moving=src@r.T+t;d,idx=tree.query(moving,workers=1);mask=d<min(threshold,np.percentile(d,80));a=moving[mask];b=ref[idx[mask]];ca=a.mean(0);cb=b.mean(0)
   u,s,vt=np.linalg.svd((a-ca).T@(b-cb));dr=vt.T@u.T
   if np.linalg.det(dr)<0:vt[-1]*=-1;dr=vt.T@u.T
   dt=cb-ca@dr.T;r=dr@r;t=t@dr.T+dt
 d,_=tree.query(src@r.T+t,workers=1);print(name,'median/p90/inlier.5',np.median(d),np.percentile(d,90),np.mean(d<.5),'rotation',r.tolist(),'t',t.tolist(),flush=True)
 T=np.eye(4);T[:3,:3]=r;T[:3,3]=t
 trans[name]={'matrix':T.tolist(),'sample_nn_median_m':float(np.median(d)),'sample_nn_p90_m':float(np.percentile(d,90)),'fraction_within_0_5m':float(np.mean(d<.5))}
trans['dufomap']={**trans['fastlio2'],'shared_transform_from':'fastlio2'}
(ROOT / 'data/mall01/display-transforms.json').write_text(json.dumps(trans,indent=2))
