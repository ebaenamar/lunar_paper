"""Pointing-jitter tolerance of the 290 GHz and 1550 nm inter-satellite links of the space-segment
companion (0.3 m apertures, 1 W, LCRNS mean 16 809 km and worst 22 433 km ranges). Margins at the
full-bandwidth rate from the companion's budget table: 290 GHz -13.7 / -16.2 dB at 2.9 Gbit/s
(LDPC rate 1/2, Eb/N0 2.2 dB); 1550 nm +15.7 / +13.2 dB at the 50 Gbit/s modem cap (9.4 photons
per bit). Pointing loss 12 (theta/theta_3dB)^2 dB with theta_3dB = 1.02 lambda/D; per-axis Gaussian
jitter, Rayleigh radial error, 99.9 % availability -> theta = 3.717 sigma; 3 dB margin retained.
Writes figs/jitter_tol.dat: largest tolerable per-axis jitter (urad) against target rate (Mbit/s)."""
import math, numpy as np
k999=math.sqrt(-2*math.log(1e-3))           # 3.717
links={"rf":(1.034e-3,2.9e9,-13.7,-16.2),"op":(1.55e-6,50e9,15.7,13.2)}  # lambda, Rfull, M_mean, M_worst
D=0.3
def sigma_max(lam,Rfull,M,R):
    th=1.02*lam/D; m=M+10*math.log10(Rfull/R)-3
    return th*math.sqrt(m/12)/k999*1e6 if (R<=Rfull and m>0) else float('nan')
Rs=np.logspace(0,math.log10(5e4),220)       # Mbit/s
with open('figs/jitter_tol.dat','w') as f:
    f.write("R rf_mean rf_worst op_mean op_worst\n")
    for R in Rs:
        v=[sigma_max(l,Rf,M,R*1e6) for (l,Rf,Mm,Mw) in links.values() for M in (Mm,Mw)]
        f.write(f"{R:.5g} "+" ".join("nan" if math.isnan(x) else f"{x:.5g}" for x in v)+"\n")
if __name__=="__main__":
    l,Rf,Mm,Mw=links["rf"]; print("RF max rate @3dB mean/worst Mbit/s", round(Rf*10**((Mm-3)/10)/1e6,1), round(Rf*10**((Mw-3)/10)/1e6,1))
    print("RF sigma at 1 Mbit/s (urad)", round(sigma_max(l,Rf,Mm,1e6)))
    l,Rf,Mm,Mw=links["op"]; print("optical sigma at 1 Mbit/s / 50 Gbit/s (urad)", round(sigma_max(l,Rf,Mm,1e6),2), round(sigma_max(l,Rf,Mm,50e9),2))
    thO=1.02*1.55e-6/D; R=links["rf"][1]*10**((links["rf"][2]-3)/10); m=15.7+10*math.log10(50e9/R)-3
    print("crossover theta* (urad)", round(thO*math.sqrt(m/12)*1e6,2), " sigma", round(thO*math.sqrt(m/12)/k999*1e6,2))
    thR=1.02*1.034e-3/D; print("RF loss at 100/270 urad sigma (dB)", round(12*(k999*100e-6/thR)**2,2), round(12*(k999*270e-6/thR)**2,2))
