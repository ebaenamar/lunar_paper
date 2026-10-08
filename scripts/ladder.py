"""Generate figs/ladder_data.tex for the frequency-ladder figure (Fig. 8).
Link model: R = Pt Gt Gr (lambda/4 pi R)^2 / (k Tsys Lo (Eb/N0)req), eta=0.6, uncoded QPSK
Eb/N0=10 dB, Lo=2 dB. Physics curves: 10 W and 500 K at every frequency. Hardware curves:
Pt = min(eff(f) * P_DC, Pmax(f)), with eff and Pmax interpolated log-log between the published
amplifiers of the ladder table (bib keys in the comments). Tsys(f) follows the table column.
'tube' = best of TWTA and SSPA at each anchor; 'sspa' = solid-state amplifiers only."""
import math, bisect, numpy as np
c=2.998e8; k=1.38e-23; eta=0.6; Lo=10**0.2; EbN0=10
def interp(pts, f):
    """log-log interpolation of (f, y) anchors, constant outside the anchor range"""
    xs=[math.log10(p[0]) for p in pts]; ys=[math.log10(p[1]) for p in pts]; x=math.log10(f)
    if x<=xs[0]: return 10**ys[0]
    if x>=xs[-1]: return 10**ys[-1]
    i=bisect.bisect(xs,x); t=(x-xs[i-1])/(xs[i]-xs[i-1]); return 10**(ys[i-1]+t*(ys[i]-ys[i-1]))
# (f [Hz], DC-to-RF efficiency, maximum RF output [W])
TUBE=[(2.5e9,0.44,300),    # GaN SSPA incl. PSU [giofre2016]
      (8.4e9,0.59,100),    # MRO X-band TWTA, flight [taylor2006mro]
      (25.65e9,0.48,40),   # LRO K-band TWTA, flight [simons2010lro]
      (32e9,0.42,200),     # MRO Ka TWTA, flight [taylor2006mro]; 200 W qualified [simons2008tm]
      (45e9,0.40,200),     # Q-band 200 W qualified [robbins2018q]; efficiency assumed
      (94e9,0.20,65),      # W-band TWT MPM, laboratory [chen2022wmpm]
      (145e9,0.12,20),     # D-band TWT 20 W, laboratory [chen2025d]; efficiency interpolated
      (233e9,0.09,32),     # 233 GHz MPM, airborne [armstrong2018]
      (290e9,0.04,2),      # ~2 W designs [paoloni2026]; efficiency assumed
      (400e9,0.01,0.5),    # assumption
      (600e9,0.002,0.05),  # assumption (sources milliwatt-class above 300 GHz)
      (1e12,0.0005,0.005)] # assumption
SSPA=[(2.5e9,0.44,300),    # [giofre2016]
      (19e9,0.24,125),     # K-band GaN SSPA, engineering model [giofre2023]
      (73e9,0.046,1),      # E-band GaN MMIC module [simons2025eband]
      (145e9,0.02,0.1),    # InP SSPA [paoloni2026]; efficiency assumed
      (290e9,0.005,0.01),  # [paoloni2026]; efficiency assumed
      (400e9,0.001,0.001), # assumption
      (1e12,0.0001,0.0001)]# assumption
TSYS=[(2e9,300),(8e9,350),(30e9,500),(80e9,800),(140e9,1500),(300e9,2500),(600e9,5000),(1e12,10000)]
def Pt(f,Pdc,anch):
    return min(interp([(a,e) for a,e,_ in anch],f)*Pdc, interp([(a,p) for a,_,p in anch],f))
def rate(f,P,T,D1,D2,R):
    lam=c/f; G1=eta*(math.pi*D1/lam)**2; G2=eta*(math.pi*D2/lam)**2
    return P*G1*G2/((4*math.pi*R/lam)**2*k*T*Lo*10**(EbN0/10))
links={"LT":(0.5,0.5,17.4e6,100),"LF":(1.0,1.0,60e6,100),"BB":(0.1,0.1,10e3,10)}  # (Dt,Dr,R,DC watts)
fs=np.logspace(9.3,12,120)
def fmt(xs,ys): return " ".join(f"({x/1e9:.4g},{max(y,1e3)/1e6:.4g})" for x,y in zip(xs,ys))
with open('figs/ladder_data.tex','w') as fh:
    for name,(D1,D2,R,Pdc) in links.items():
        fh.write(f"\\def\\{name}phys{{{fmt(fs,[rate(f,10,500,D1,D2,R) for f in fs])}}}\n")
        fh.write(f"\\def\\{name}hw{{{fmt(fs,[rate(f,Pt(f,Pdc,TUBE),interp(TSYS,f),D1,D2,R) for f in fs])}}}\n")
        fh.write(f"\\def\\{name}sspa{{{fmt(fs,[rate(f,Pt(f,Pdc,SSPA),interp(TSYS,f),D1,D2,R) for f in fs])}}}\n")
if __name__=="__main__":
    for name,(D1,D2,R,Pdc) in links.items():
        hw=[rate(f,Pt(f,Pdc,TUBE),interp(TSYS,f),D1,D2,R) for f in fs]; ss=[rate(f,Pt(f,Pdc,SSPA),interp(TSYS,f),D1,D2,R) for f in fs]
        i=int(np.argmax(hw)); j=int(np.argmax(ss))
        print(f"{name}: tube peak {hw[i]/1e6:.0f} Mbit/s at {fs[i]/1e9:.0f} GHz; SSPA peak {ss[j]/1e6:.0f} Mbit/s at {fs[j]/1e9:.0f} GHz")
        band=[r for f,r in zip(fs,hw) if 73e9<=f<=240e9]; print(f"   tube spread 73-240 GHz: {10*math.log10(max(band)/min(band)):.1f} dB")
    print("wrote figs/ladder_data.tex")
