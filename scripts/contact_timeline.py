"""Contact timeline of the LCRNS reference constellation seen from Malapert Peak (Fig. 5), from the
90-day GMAT topocentric outputs of the space-segment companion (data/topo_SV*_Malapert.txt).
Visibility above a 5 deg mask on a 5-min grid; PDOP with a receiver-clock state.
Writes figs/contact_range.dat (slant range per satellite, nan when not in view, first lunar day)
and figs/contact_count.dat (satellites in view and PDOP); prints 90-day statistics."""
import numpy as np
SV=[1,2,3,4,5]; dt=5/1440.0
raw={s:np.loadtxt(f'data/topo_SV{s}_Malapert.txt',skiprows=1) for s in SV}
t0=max(raw[s][0,0] for s in SV); t1=min(raw[s][-1,0] for s in SV)
tg=np.arange(t0,t1,dt)
pos={s:np.stack([np.interp(tg,raw[s][:,0],raw[s][:,k]) for k in (1,2,3)],1) for s in SV}
rng={s:np.linalg.norm(pos[s],axis=1) for s in SV}
vis={s:np.degrees(np.arcsin(pos[s][:,2]/rng[s]))>=5.0 for s in SV}
n=np.sum([vis[s] for s in SV],0)
pdop=np.full(len(tg),np.nan)
for i in range(len(tg)):
    us=[pos[s][i]/rng[s][i] for s in SV if vis[s][i]]
    if len(us)>=4:
        H=np.hstack([-np.array(us),np.ones((len(us),1))])
        Q=np.linalg.inv(H.T@H); pdop[i]=np.sqrt(np.trace(Q[:3,:3]))
day=29.530589; m=(tg-t0)<=day
with open('figs/contact_range.dat','w') as f:
    f.write("t_d "+" ".join(f"sv{s}" for s in SV)+"\n")
    for i in np.where(m)[0][::2]:
        f.write(f"{tg[i]-t0:.4f} "+" ".join(f"{rng[s][i]/1e3:.3f}" if vis[s][i] else "nan" for s in SV)+"\n")
with open('figs/contact_count.dat','w') as f:
    f.write("t_d n pdop\n")
    for i in np.where(m)[0][::2]:
        f.write(f"{tg[i]-t0:.4f} {n[i]} "+(f"{min(pdop[i],50):.3f}" if np.isfinite(pdop[i]) else "nan")+"\n")
if __name__=="__main__":
    print("90 d: >=1 %.1f%%, >=4 %.1f%%, mean N %.2f, PDOP median %.2f, PDOP<=6 %.1f%%"%(
        100*(n>=1).mean(),100*(n>=4).mean(),n.mean(),np.nanmedian(pdop),100*np.nanmean(np.where(np.isfinite(pdop),pdop<=6,False))))
    print("single-satellite duty cycles:", [round(vis[s].mean(),3) for s in SV])
