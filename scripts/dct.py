#!/usr/bin/env python3
"""dct.py -- design-control table and worked budgets for Section VII / Appendix B.

One parameter dictionary (PARAMS) drives every number: the Appendix B
design-control table (written to figs/dct_table.tex), the 810-005 recomputation of
the Ka-band trunk, the LRO flown example, the link 1-3-5 chain, and the
clipping ranges of Fig. 10. Run from the repository root:  python3 scripts/dct.py
Conventions follow Section VII: eta = 0.6, theta_3dB = 70 lambda/D,
uncoded QPSK (Eb/N0)req = 10 dB at BER 1e-5, Lo lumps all non-free-space losses.
"""
from math import log10, pi, sqrt, exp, sin, radians

C, K_DB, K_LIN = 2.998e8, -228.6, 1.380649e-23

# ----------------------------------------------------------------------------
# Parameter dictionary
# ----------------------------------------------------------------------------
PARAMS = {
    "common": {"eta": 0.6, "ebn0_req_db": 10.0, "margin_target_db": 3.0,
               "pointing_loss_per_end_db": 0.5},
    # Appendix B columns. dt/dr in m (None = omni, gain given in g*_dbi);
    # gr_dbi/tsys_k given explicitly for DSN ends (810-005 values).
    "links": {
        "1 S":   dict(f=2.579e9, r=10e3, pt=1.0, dt=None, gt_dbi=0.0, dr=None, gr_dbi=3.0,
                      tsys=290.0, lo=2.0, rb=1e6),
        "2 S":   dict(f=2.2e9, r=17.4e6, pt=10.0, dt=0.5, dr=0.5, tsys=500.0, lo=2.0, rb=1e5),
        "3 Ka":  dict(f=26e9, r=17.4e6, pt=10.0, dt=0.5, dr=0.5, tsys=500.0, lo=2.0, rb=10e6),
        "4 Ka":  dict(f=26e9, r=60e6, pt=10.0, dt=1.0, dr=1.0, tsys=500.0, lo=2.0, rb=20e6),
        "5 Ka":  dict(f=26.25e9, r=384.4e6, pt=40.0, dt=0.75, dr=34.0, gr_dbi=77.23,  # Lo: 2 dB + 0.18 dB zenith
                      hpbw_r=0.021, tsys=45.4, lo=2.176, rb=100e6),                   # atmosphere (Canberra, CD 0.25)
        "6 X":   dict(f=8.45e9, r=384.4e6, pt=20.0, dt=0.6, dr=34.0, gr_dbi=68.32,
                      hpbw_r=0.066, tsys=21.25, lo=2.0, rb=100e6),
        "3 E":   dict(f=81e9, r=17.4e6, pt=10.0, dt=0.5, dr=0.5, tsys=800.0, lo=2.0, rb=50e6),
        "3 D":   dict(f=140e9, r=17.4e6, pt=10.0, dt=0.5, dr=0.5, tsys=1500.0, lo=2.0, rb=100e6),
        "4 E":   dict(f=81e9, r=60e6, pt=10.0, dt=1.0, dr=1.0, tsys=800.0, lo=2.0, rb=100e6),
        "4 D":   dict(f=140e9, r=60e6, pt=10.0, dt=1.0, dr=1.0, tsys=1500.0, lo=2.0, rb=200e6),
    },
    # DSN 810-005 module 104 Rev. Q (3 Aug 2026), Table A-3, DSS-34 K-only HEMT-1 RCP,
    # 26.25 GHz diplexed; module 105 Rev. E Tables 20 / A-5 (Canberra, 26 GHz Azen).
    "dss34_k": dict(g0=77.68, g1=0.00025, gamma=47.8, t1=32.4, t2=-40.0, a=0.20,
                    azen={0.25: 0.176, 0.50: 0.212, 0.90: 0.387, 0.99: 1.213}),
    "moon_noise_k": 150.0,   # module 105 Rev. E, Sec. 2.4.2: Tb 240 K x 0.9 x 0.7
    "trunk": dict(f=26.25e9, r=384.4e6, r_max=384.4e6 + 1737e3 + 17.4e6,
                  pt=40.0, dt=0.75, lo=2.0, rb=100e6),
    # LRO K-band downlink (flown 2009-present). Sources: Morabito & Heckman IPN PR
    # 42-211A, Morabito IPN PR 42-222B; NEN Users' Guide 453-NENUG Rev. 4 Table 9-3;
    # Force et al. LRO TWTA. Lunar noise: Tb = 275 K (adverse) / 0.42 x 275 K.
    "lro": dict(f=25.65e9, pt=40.0, dt=0.75, gt_spec_g_over_t=45.0, g_over_t_tbl=46.98,
                gr_ws1=70.5, r_fav=354_152e3, r_adv=411_154e3, tb_adv=275.0, tb_fav=0.42 * 275.0,
                azen_fav=0.150, azen_adv=0.284, el=50.0, lo=2.0, rb=100e6, rs=228.7e6,
                ebn0_req_coded=2.5),
    # Chain example (links 1, 3, 5)
    "chain": dict(cell_delay_s=10e-3, relay_processing_s=1.0, duty_relay=0.83,
                  trunk_pass_h=8.0, orbit_h=30.0, rover_rate=1e6),
}

# ----------------------------------------------------------------------------
# Primitives
# ----------------------------------------------------------------------------
def db(x): return 10 * log10(x)
def lam(f): return C / f
def gain_dbi(d, f, eta=0.6): return db(eta * (pi * d / lam(f)) ** 2)
def hpbw_deg(d, f): return 70 * lam(f) / d
def fspl_db(r, f): return 20 * log10(4 * pi * r * f / C)
def point_req_deg(hpbw, loss_db): return hpbw * sqrt(loss_db / 12.0)


def budget(p, eta=0.6, req=10.0):
    gt = p.get("gt_dbi", gain_dbi(p["dt"], p["f"], eta) if p.get("dt") else 0.0)
    gr = p.get("gr_dbi", gain_dbi(p["dr"], p["f"], eta) if p.get("dr") else 0.0)
    lfs = fspl_db(p["r"], p["f"])
    eirp = db(p["pt"]) + gt
    gt_ratio = gr - db(p["tsys"])
    cn0 = eirp + gt_ratio - lfs - p["lo"] - K_DB
    ebn0 = cn0 - db(p["rb"])
    bw_t = hpbw_deg(p["dt"], p["f"]) if p.get("dt") else None
    bw_r = p.get("hpbw_r", hpbw_deg(p["dr"], p["f"]) if p.get("dr") else None)
    return dict(f=p["f"], r=p["r"], pt=db(p["pt"]), gt=gt, eirp=eirp, lfs=lfs, lo=p["lo"],
                gr=gr, tsys=p["tsys"], gt_ratio=gt_ratio, cn0=cn0, rb=p["rb"], ebn0=ebn0,
                req=req, margin=ebn0 - req, r3=10 ** ((cn0 - req - 3.0) / 10),
                bw_t=bw_t, bw_r=bw_r)


def dsn_gain(el, d, azen):  # module 104 Eq. (A-1) without the atmospheric term
    return d["g0"] - d["g1"] * (el - d["gamma"]) ** 2


def dsn_top(el, d, azen, cd):  # module 104 Eqs. (A2)-(A9)
    l = 10 ** (azen / sin(radians(el)) / 10)
    return d["t1"] + d["t2"] * exp(-d["a"] * el) + (255 + 25 * cd) * (1 - 1 / l) + 2.725 / l


# ----------------------------------------------------------------------------
# Appendix B table
# ----------------------------------------------------------------------------
def fmt_rate(x):
    return f"{x/1e9:.2g}\\,G" if x >= 1e9 else f"{x/1e6:.3g}\\,M" if x >= 1e6 else f"{x/1e3:.3g}\\,k"


def fmt_bw(b):
    if b["bw_t"] is None and b["bw_r"] is None:
        return "omni"
    t = "omni" if b["bw_t"] is None else f"{b['bw_t']:.2g}"
    r = "omni" if b["bw_r"] is None else f"{b['bw_r']:.2g}"
    return t if t == r else f"{t}/{r}"


def fmt_pt(b, loss):
    vals = [x for x in (b["bw_t"], b["bw_r"]) if x is not None]
    if not vals:
        return "---"
    t = "---" if b["bw_t"] is None else f"{point_req_deg(b['bw_t'], loss):.2g}"
    r = "---" if b["bw_r"] is None else f"{point_req_deg(b['bw_r'], loss):.2g}"
    return t if t == r else f"{t}/{r}"


def dct_latex(P):
    com = P["common"]
    cols = {k: budget(v, com["eta"], com["ebn0_req_db"]) for k, v in P["links"].items()}
    names = list(cols)
    rows = [
        ("Frequency (GHz)", lambda b: f"{b['f']/1e9:.4g}"),
        ("Range (km)", lambda b: f"{b['r']/1e3:,.0f}".replace(",", "\\,")),
        ("$P_t$ (dBW)", lambda b: f"{b['pt']:.1f}"),
        ("$G_t$ (dBi)", lambda b: f"{b['gt']:.1f}"),
        ("EIRP (dBW)", lambda b: f"{b['eirp']:.1f}"),
        ("$L_{\\mathrm{FS}}$ (dB)", lambda b: f"{b['lfs']:.1f}"),
        ("$L_{\\mathrm{o}}$ (dB)", lambda b: f"{b['lo']:.1f}"),
        ("$G_r$ (dBi)", lambda b: f"{b['gr']:.1f}"),
        ("$T_{\\mathrm{sys}}$ (K)", lambda b: f"{b['tsys']:.4g}"),
        ("$G/T$ (dB/K)", lambda b: f"{b['gt_ratio']:.1f}"),
        ("$C/N_0$ (dBHz)", lambda b: f"{b['cn0']:.1f}"),
        ("$R_b$ (bit/s)", lambda b: fmt_rate(b["rb"])),
        ("$E_b/N_0$ (dB)", lambda b: f"{b['ebn0']:.1f}"),
        ("Required (dB)", lambda b: f"{b['req']:.1f}"),
        ("Margin (dB)", lambda b: f"{b['margin']:.1f}"),
        ("$R_b$ at 3\\,dB margin", lambda b: fmt_rate(b["r3"])),
        ("$\\theta_{3\\mathrm{dB}}$, Tx/Rx (deg)", fmt_bw),
        ("Pointing, Tx/Rx (deg)", lambda b: fmt_pt(b, com["pointing_loss_per_end_db"])),
    ]
    head = " & ".join(["Quantity"] + [f"L{n.split()[0]}\\,{n.split()[1]}" for n in names])
    out = ["% Generated by dct.py -- do not edit by hand",
           "\\begin{table*}[!t]",
           "\\caption{Design-Control Table for the Six Canonical Links}",
           "\\label{tab:dct}", "\\centering", "\\scriptsize", "\\setlength{\\tabcolsep}{3pt}",
           "\\begin{tabular}{@{}l" + "r" * len(names) + "@{}}", "\\toprule", head + " \\\\",
           "\\midrule"]
    for label, fn in rows:
        out.append(" & ".join([label] + [fn(cols[n]) for n in names]) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "\\end{table*}"]
    return "\n".join(out), cols


# ----------------------------------------------------------------------------
# Worked budgets printed for the text
# ----------------------------------------------------------------------------
def trunk_810(P):
    t, d = P["trunk"], P["dss34_k"]
    gt = gain_dbi(t["dt"], t["f"])
    rows = []
    cases = [("Table 12 (v2)", None, None, False, t["r"]),
             ("Zenith, CD 0.25", 90, 0.25, False, t["r"]),
             ("20 deg, CD 0.90", 20, 0.90, False, t["r"]),
             ("20 deg, CD 0.99", 20, 0.99, False, t["r"]),
             ("10 deg, CD 0.99", 10, 0.99, False, t["r"]),
             ("20 deg, CD 0.90, Moon in beam", 20, 0.90, True, t["r"]),
             ("20 deg, CD 0.90, max range", 20, 0.90, False, t["r_max"])]
    for name, el, cd, moon, r in cases:
        if el is None:
            gr, top, atm, f = gain_dbi(34, 26e9), 44.0, 0.0, 26e9
        else:
            az = d["azen"][cd]
            gr, top, atm, f = dsn_gain(el, d, az), dsn_top(el, d, az, cd), az / sin(radians(el)), t["f"]
        if moon:
            top += P["moon_noise_k"]
        cn0 = db(t["pt"]) + gain_dbi(t["dt"], f) + gr - db(top) - fspl_db(r, f) - t["lo"] - atm - K_DB
        ebn0 = cn0 - db(t["rb"])
        rows.append((name, gr, top, gr - db(top), atm, fspl_db(r, f), cn0, ebn0, ebn0 - 10,
                     10 ** ((cn0 - 13) / 10)))
    return gt, rows


def lro(P):
    p = P["lro"]
    gt = gain_dbi(p["dt"], p["f"])
    tsys0 = 10 ** ((p["gr_ws1"] - p["g_over_t_tbl"]) / 10)
    out = {}
    for case, r, tb, az in (("favorable", p["r_fav"], p["tb_fav"], p["azen_fav"]),
                            ("adverse", p["r_adv"], p["tb_adv"], p["azen_adv"])):
        tmoon = tb * 0.9 * 0.7
        g_t = p["g_over_t_tbl"] - db((tsys0 + tmoon) / tsys0)
        atm = az / sin(radians(p["el"]))
        cn0 = db(p["pt"]) + gt + g_t - fspl_db(r, p["f"]) - p["lo"] - atm - K_DB
        ebn0 = cn0 - db(p["rb"])
        out[case] = dict(tmoon=tmoon, g_t=g_t, lfs=fspl_db(r, p["f"]), atm=atm, cn0=cn0,
                         ebn0=ebn0, es_n0_sym=cn0 - db(p["rs"]),
                         margin_coded=ebn0 - p["ebn0_req_coded"])
    return gt, tsys0, out


def chain(P, cols):
    c = P["chain"]
    l1, l3, l5 = cols["1 S"], cols["3 Ka"], cols["5 Ka"]
    duty5 = c["trunk_pass_h"] / 24.0
    hops = [("1 rover-gateway", l1["rb"], l1["margin"], l1["r3"], c["cell_delay_s"] + l1["r"] / C, 1.0),
            ("3 gateway-relay", l3["rb"], l3["margin"], l3["r3"], l3["r"] / C + c["relay_processing_s"], c["duty_relay"]),
            ("5 relay-Earth", l5["rb"], l5["margin"], l5["r3"], l5["r"] / C, duty5)]
    gap3 = (1 - c["duty_relay"]) * c["orbit_h"] * 3600
    gap5 = (24 - c["trunk_pass_h"]) * 3600
    return hops, gap3, gap5


def fig10_rmin(rates=(1e6, 10e6, 100e6), f=26e9, dr=0.5, tsys=500, pt=10, lo=2, req=13, eta=0.6):  # Fig. 10: 0.5 m relay receiver
    l = lam(f)
    out = {}
    for rb in rates:
        k = 4 * l / (pi * eta * dr) * sqrt(K_LIN * tsys * rb * 10 ** (lo / 10) * 10 ** (req / 10) / pt)
        out[rb] = l / k / 1e3  # km where D_t = lambda
    return l, out


if __name__ == "__main__":
    tex, cols = dct_latex(PARAMS)
    open("figs/dct_table.tex", "w").write(tex + "\n")
    print("== Appendix B columns ==")
    for n, b in cols.items():
        print(f"{n:6s} EIRP {b['eirp']:6.1f}  G/T {b['gt_ratio']:6.1f}  C/N0 {b['cn0']:6.1f}  "
              f"Eb/N0 {b['ebn0']:5.1f}  M {b['margin']:5.1f}  R3 {b['r3']/1e6:9.3f} Mbps  "
              f"bw {b['bw_t'] or 0:.3f}/{b['bw_r'] or 0:.3f}")
    gt, rows = trunk_810(PARAMS)
    print(f"\n== Trunk vs 810-005 (Gt = {gt:.1f} dBi) ==")
    for r in rows:
        print("%-32s Gr %5.2f Top %6.1f G/T %5.1f Atm %4.2f LFS %6.1f C/N0 %6.1f Eb/N0 %5.1f M %5.1f R@3dB %7.2f Gbps"
              % (r[0], *r[1:9], r[9] / 1e9))
    gt, ts0, lr = lro(PARAMS)
    print(f"\n== LRO (Gt {gt:.1f} dBi, WS1 Tsys {ts0:.0f} K) ==")
    for k, v in lr.items():
        print(k, {a: round(b, 2) for a, b in v.items()})
    hops, gap3, gap5 = chain(PARAMS, cols)
    print("\n== Chain 1-3-5 ==")
    for h in hops:
        print("%-16s Rb %8.2f Mbps M %5.1f R@3dB %9.2f Mbps delay %.3f s duty %.2f avg %8.2f Mbps"
              % (h[0], h[1] / 1e6, h[2], h[3] / 1e6, h[4], h[5], h[1] * h[5] / 1e6))
    print("one-way real-time delay %.3f s; link-3 gap %.1f h; trunk gap %.1f h" %
          (sum(h[4] for h in hops), gap3 / 3600, gap5 / 3600))
    print("gateway buffer for 1 Mbps over link-3 gap: %.2f GB" % (1e6 * gap3 / 8e9))
    agg = hops[1][1] * hops[1][5]
    print("relay buffer for %.1f Mbps over trunk gap: %.1f GB; trunk drain needs %.1f Mbps"
          % (agg / 1e6, agg * gap5 / 8e9, agg / hops[2][5] / 1e6))
    # 99.9 % availability check of Sec. VII-D: ITU-R P.618 slant attenuation at 20 deg
    # quoted in v2 (8.6 / 19.1 / 10.7 dB), with the sky-noise rise that accompanies it.
    t, d = PARAMS["trunk"], PARAMS["dss34_k"]
    base = rows[1][8]  # zenith CD 0.25 margin
    print("\n== 99.9 %% check at 20 deg (zenith-clear margin %.1f dB) ==" % base)
    for site, a in (("Goldstone", 8.6), ("Canberra", 19.1), ("Madrid", 10.7)):
        top = d["t1"] + d["t2"] * exp(-d["a"] * 20) + 279.0 * (1 - 10 ** (-a / 10))
        dg = dsn_gain(20, d, 0) - dsn_gain(90, d, 0)
        m = base + rows[1][4] - a + dg - db(top / rows[1][2])
        print(f"{site:10s} A {a:5.1f} dB  Top {top:6.1f} K  noise rise {db(top/rows[1][2]):4.1f} dB  margin {m:5.1f} dB"
              f"  (attenuation only: {base + rows[1][4] - a:5.1f})")
    l, rm = fig10_rmin()
    print("\n== Fig. 10: lambda = %.5f m; D_t = lambda at R =" % l,
          {f"{k/1e6:g} Mbps": round(v, 1) for k, v in rm.items()}, "km")
