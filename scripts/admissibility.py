"""Traffic admissibility over a single LCRNS relay (Fig. 14). Contact plan: SV1 of the LCRNS
reference constellation seen from Malapert Peak above a 5 deg mask, from the 90-day GMAT
propagation of the space-segment companion (data/topo_SV1_Malapert.txt). Delivery of a class
with bundle lifetime L and offered rate R (protocol companion, closed form):
  P(L,R) = min(P_gap(L), C_eff/R),  P_gap(L) = (sum c_i + sum min(L, g_j)) / T,
with contacts c_i, gaps g_j, span T and effective backhaul C_eff = duty cycle x 10 Mbit/s.
Writes figs/admiss_contours.dat (lifetime L_p at which P_gap reaches p) and prints the plan."""
import numpy as np
d=np.loadtxt('data/topo_SV1_Malapert.txt',skiprows=1); t=d[:,0]*24.0
r=d[:,1:4]; el=np.degrees(np.arcsin(r[:,2]/np.linalg.norm(r,axis=1)))
tg=np.arange(t[0],t[-1],1/60); v=np.interp(tg,t,el)>=5.0
e=np.diff(v.astype(int)); s=list(np.where(e==1)[0]+1); f=list(np.where(e==-1)[0]+1)
if v[0]: s=[0]+s
if v[-1]: f=f+[len(v)]
gaps=np.array([tg[s[i+1]]-tg[f[i]] for i in range(len(f)) if i+1<len(s)])
T=tg[-1]-tg[0]; duty=v.mean(); C=duty*10.0
def Pgap(L): return duty+np.minimum(L,gaps).sum()/T
ps=[0.85,0.90,0.95,0.99]
def Lp(p):
    lo,hi=0.0,gaps.max()
    for _ in range(60):
        m=(lo+hi)/2; lo,hi=(m,hi) if Pgap(m)<p else (lo,m)
    return hi
with open('figs/admiss_contours.dat','w') as fh:
    fh.write("p Lp_h Rmax_Mbps\n")
    for p in ps: fh.write(f"{p} {Lp(p):.4f} {C/p:.4f}\n")
if __name__=="__main__":
    print(f"duty {duty:.3f}  C_eff {C:.2f} Mbit/s  gaps {len(gaps)}  median {np.median(gaps):.2f} h  max {gaps.max():.2f} h")
    for p in ps: print(p, round(Lp(p),2),'h', round(C/p,2),'Mbit/s')
    for name,L in (("emergency 300 s",300/3600),("media 3.28 h",3.28)): print(name, round(Pgap(L),3))
