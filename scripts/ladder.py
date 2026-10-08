"""Generate figs/ladder_data.tex for the frequency-ladder figure.
Assumptions: eta=0.6, uncoded QPSK Eb/N0=10 dB, Lo=2 dB. Hardware curve: constant DC power with
band-dependent DC-to-RF efficiency eff(f) and receiver noise temperature Tsys(f); edit the anchor
points below as the hardware columns of the ladder table are cited."""
import math, bisect, numpy as np
c=2.998e8; k=1.38e-23; eta=0.6; Lo=10**0.2; EbN0=10
def interp_log(pts, f, logy=False):
    xs=[math.log10(p[0]) for p in pts]; ys=[math.log10(p[1]) if logy else p[1] for p in pts]
    x=math.log10(f)
    if x<=xs[0]: y=ys[0]
    elif x>=xs[-1]: y=ys[-1]
    else:
        i=bisect.bisect(xs,x); t=(x-xs[i-1])/(xs[i]-xs[i-1]); y=ys[i-1]+t*(ys[i]-ys[i-1])
    return 10**y if logy else y
EFF=[(2e9,0.6),(8e9,0.55),(30e9,0.5),(45e9,0.45),(80e9,0.35),(100e9,0.3),(140e9,0.25),(170e9,0.22),(220e9,0.15),(300e9,0.08),(600e9,0.01),(1e12,0.002)]
TSYS=[(2e9,300),(8e9,350),(30e9,500),(80e9,800),(140e9,1500),(300e9,2500),(600e9,5000),(1e12,10000)]
def eff(f): return 10**interp_log([(a,math.log10(b)) for a,b in EFF], f)
def Tsys(f): return interp_log(TSYS, f, logy=True)
def rate(f,P,T,D1,D2,R):
    lam=c/f; G1=eta*(math.pi*D1/lam)**2; G2=eta*(math.pi*D2/lam)**2
    return P*G1*G2/((4*math.pi*R/lam)**2*k*T*Lo*10**(EbN0/10))
links={"LT":(0.5,0.5,17.4e6,100),"LF":(1.0,1.0,60e6,100),"BB":(0.1,0.1,10e3,10)}  # name:(Dt,Dr,R,DC watts)
fs=np.logspace(9.3,12,120)
def fmt(xs,ys): return " ".join(f"({x/1e9:.4g},{max(y,1e3)/1e6:.4g})" for x,y in zip(xs,ys))
with open('figs/ladder_data.tex','w') as fh:
    for name,(D1,D2,R,Pdc) in links.items():
        fh.write(f"\\def\\{name}phys{{{fmt(fs,[rate(f,10,500,D1,D2,R) for f in fs])}}}\n")
        fh.write(f"\\def\\{name}hw{{{fmt(fs,[rate(f,Pdc*eff(f),Tsys(f),D1,D2,R) for f in fs])}}}\n")
print("wrote figs/ladder_data.tex")
