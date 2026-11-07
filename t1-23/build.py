#!/usr/bin/env python3
"""Generează raportul pentru Tema S1 (RCI) – N = 27, conf. Bogdan Cristian Florea.

Rulare:  python3 build.py           -> report.html + Tema_S1_N27.pdf (prin Chrome headless)
Datele manuale (WoS, Scopus, ResearchGate, conturile personale) se completează în data/manual.json,
iar capturile de ecran se pun în screenshots/ cu numele listate în raport.
"""
import csv, html, json, os, subprocess, sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
SHOTS = os.path.join(ROOT, "screenshots")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

GS_URL = "https://scholar.google.com/citations?user=y4Ho9CIAAAAJ"
ORCID_N = "0000-0002-1113-6400"
SCOPUS_N = "35315667300"
OPENALEX_N = "A5054838804"
RG_N = "https://www.researchgate.net/profile/Bogdan-Florea"
DATA_COLECTARE = "07.11.2026"

# Indicatori agregați Google Scholar (tabelul „Cited by” din profil, colectat la DATA_COLECTARE)
GS_STATS = {"citari": (598, 501), "h": (10, 9), "i10": (11, 9)}
GS_HIST = dict(zip(range(2013, 2027), [3, 6, 6, 3, 6, 13, 22, 34, 44, 61, 65, 98, 131, 94]))


def h_index(cits):
    s = sorted((c for c in cits if c is not None), reverse=True)
    return sum(1 for i, c in enumerate(s, 1) if c >= i)


def i10(cits):
    return sum(1 for c in cits if c and c >= 10)


def esc(s):
    return html.escape(str(s))


# ---------------------------------------------------------------- încărcare date
def load():
    with open(os.path.join(DATA, "gs_florea.tsv"), encoding="utf-8") as f:
        gs = [dict(c=int(r["citari"]), y=r["an"], t=r["titlu"]) for r in csv.DictReader(f, delimiter="\t")]
    with open(os.path.join(DATA, "openalex_florea.json"), encoding="utf-8") as f:
        oa = json.load(f)
    with open(os.path.join(DATA, "manual.json"), encoding="utf-8") as f:
        man = json.load(f)
    return gs, oa, man


# ---------------------------------------------------------------- grafice SVG
def svg_hindex(items, title, color="#2b6cb0", self_color="#e53e3e", max_bars=24):
    """items: listă de (citări_totale, autocitări). Bare sortate descrescător, dreapta y=x, nucleul h evidențiat."""
    items = sorted(items, key=lambda x: -x[0])[:max_bars]
    if not items:
        return ""
    W, H, L, B, T, R = 720, 300, 48, 40, 34, 14
    n = len(items)
    ymax = max(10, max(c for c, _ in items))
    ymax = int(ymax * 1.1) + 1
    bw = (W - L - R) / n
    sy = lambda v: T + (H - T - B) * (1 - v / ymax)
    h_all = h_index([c for c, _ in items])
    h_ns = h_index([c - s for c, s in items])
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">',
           f'<text x="{L}" y="18" class="ct">{esc(title)}</text>']
    # grid
    step = max(1, round(ymax / 5 / 5) * 5) if ymax > 25 else max(1, ymax // 5)
    v = 0
    while v <= ymax:
        y = sy(v)
        out.append(f'<line x1="{L}" x2="{W-R}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                   f'<text x="{L-6}" y="{y+4:.1f}" class="ax" text-anchor="end">{v}</text>')
        v += step
    # nucleul h (zona pătrată h x h)
    if h_all:
        out.append(f'<rect x="{L}" y="{sy(h_all):.1f}" width="{bw*h_all:.1f}" height="{sy(0)-sy(h_all):.1f}" '
                   f'class="hcore"/>')
    for i, (c, s) in enumerate(items):
        x = L + i * bw + bw * 0.12
        w = bw * 0.76
        ns = c - s
        out.append(f'<rect x="{x:.1f}" y="{sy(ns):.1f}" width="{w:.1f}" height="{sy(0)-sy(ns):.1f}" fill="{color}" '
                   f'opacity="{1 if i < h_all else .45}"><title>#{i+1}: {c} citări ({s} autocitări)</title></rect>')
        if s:
            out.append(f'<rect x="{x:.1f}" y="{sy(c):.1f}" width="{w:.1f}" height="{sy(ns)-sy(c):.1f}" fill="{self_color}"/>')
        out.append(f'<text x="{x+w/2:.1f}" y="{H-B+14}" class="ax" text-anchor="middle">{i+1}</text>')
        if c >= ymax * 0.06:
            out.append(f'<text x="{x+w/2:.1f}" y="{sy(c)-3:.1f}" class="val" text-anchor="middle">{c}</text>')
    # dreapta citări = rang
    x2 = min(n, ymax)
    out.append(f'<line x1="{L}" y1="{sy(0):.1f}" x2="{L+bw*x2:.1f}" y2="{sy(x2):.1f}" class="diag"/>')
    out.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" class="ax" text-anchor="middle">rangul articolului (sortat descrescător după citări)</text>')
    lab = f"h = {h_all}" + (f"  ·  h fără autocitări = {h_ns}" if any(s for _, s in items) else "")
    out.append(f'<text x="{W-R}" y="18" class="hl" text-anchor="end">{lab}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_years(hist, title, color="#2b6cb0"):
    W, H, L, B, T, R = 720, 220, 40, 30, 30, 10
    ys = list(hist)
    ymax = int(max(hist.values()) * 1.15) + 1
    bw = (W - L - R) / len(ys)
    sy = lambda v: T + (H - T - B) * (1 - v / ymax)
    o = [f'<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">',
         f'<text x="{L}" y="18" class="ct">{esc(title)}</text>']
    for v in range(0, ymax, 25):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/>'
                 f'<text x="{L-6}" y="{sy(v)+4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for i, y in enumerate(ys):
        x = L + i * bw + bw * .15
        v = hist[y]
        o.append(f'<rect x="{x:.1f}" y="{sy(v):.1f}" width="{bw*.7:.1f}" height="{sy(0)-sy(v):.1f}" fill="{color}"/>'
                 f'<text x="{x+bw*.35:.1f}" y="{sy(v)-3:.1f}" class="val" text-anchor="middle">{v}</text>'
                 f'<text x="{x+bw*.35:.1f}" y="{H-B+14}" class="ax" text-anchor="middle">{y}</text>')
    o.append("</svg>")
    return "".join(o)


def svg_compare(rows, title):
    """rows: [(etichetă, h, h_fara_auto)] – valorile None sunt afișate ca „în așteptare”."""
    W, rowh, L = 720, 34, 210
    H = 40 + rowh * len(rows) + 10
    vmax = max([v for r in rows for v in r[1:] if v] + [12])
    sx = lambda v: L + (W - L - 60) * v / vmax
    o = [f'<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">',
         f'<text x="10" y="18" class="ct">{esc(title)}</text>',
         f'<rect x="{W-250}" y="8" width="10" height="10" fill="#2b6cb0"/><text x="{W-235}" y="17" class="ax">cu autocitări</text>',
         f'<rect x="{W-140}" y="8" width="10" height="10" fill="#38a169"/><text x="{W-125}" y="17" class="ax">fără autocitări</text>']
    for i, (lab, a, b) in enumerate(rows):
        y = 40 + i * rowh
        o.append(f'<text x="{L-8}" y="{y+18}" class="ax" text-anchor="end">{esc(lab)}</text>')
        for j, (v, col) in enumerate(((a, "#2b6cb0"), (b, "#38a169"))):
            yy = y + 3 + j * 14
            if v is None:
                o.append(f'<text x="{L+4}" y="{yy+10}" class="pend">în așteptare (date de completat)</text>' if j == 0 else "")
            else:
                o.append(f'<rect x="{L}" y="{yy}" width="{sx(v)-L:.1f}" height="12" fill="{col}"/>'
                         f'<text x="{sx(v)+4:.1f}" y="{yy+10}" class="val">{v}</text>')
    o.append("</svg>")
    return "".join(o)


# ---------------------------------------------------------------- fragmente HTML
def shot(fname, caption, what):
    p = os.path.join(SHOTS, fname)
    if os.path.exists(p):
        return f'<figure><img src="screenshots/{esc(fname)}"/><figcaption>{esc(caption)}</figcaption></figure>'
    return (f'<div class="ph"><b>Captură de ecran: {esc(caption)}</b><br/>Fișier așteptat: '
            f'<code>screenshots/{esc(fname)}</code><br/><span>{esc(what)}</span></div>')


def val(v, unit=""):
    return f"{v}{unit}" if v not in (None, "") else '<span class="todo">de completat</span>'


def manual_items(block):
    """Citări per articol introduse manual (listă de [total, autocitări] sau de numere)."""
    lst = block.get("citari_per_articol")
    if not lst:
        return None
    return [(x[0], x[1]) if isinstance(x, (list, tuple)) else (x, 0) for x in lst]


def build():
    gs, oa, man = load()
    st, cn = man["student"], man["caz_n"]

    gs_c = [p["c"] for p in gs]
    h_gs = h_index(gs_c)
    oa_items = [(w["cited"], w["self"]) for w in oa]
    h_oa = h_index([c for c, _ in oa_items])
    h_oa_ns = h_index([c - s for c, s in oa_items])
    oa_tot = sum(c for c, _ in oa_items)
    oa_self = sum(s for _, s in oa_items)

    # citările GS fără autocitări – estimare: scădem autocitările identificate în OpenAlex pe același titlu
    norm = lambda t: "".join(ch for ch in t.lower() if ch.isalnum())[:40]
    oa_self_by = {norm(w["title"] or ""): w["self"] for w in oa}
    gs_items = [(p["c"], min(p["c"], oa_self_by.get(norm(p["t"]), 0))) for p in gs]
    h_gs_ns_est = h_index([c - s for c, s in gs_items])

    wos, sco, rg = cn["wos"], cn["scopus"], cn["researchgate"]

    charts = {
        "gs": svg_hindex(gs_items, "Fig. 1 – Google Scholar: citări per articol (roșu = autocitări identificate)"),
        "oa": svg_hindex(oa_items, "Fig. 2 – OpenAlex (index deschis, sursă suplimentară): citări per articol", color="#6b46c1"),
        "years": svg_years(GS_HIST, "Fig. 3 – Google Scholar: citări primite pe ani (2013–2026)"),
    }
    for key, blk, lab, col in (("wos", wos, "Web of Science", "#c05621"), ("sco", sco, "Scopus", "#dd6b20"),
                               ("rg", rg, "ResearchGate", "#00a3a3")):
        it = manual_items(blk)
        charts[key] = svg_hindex(it, f"{lab}: citări per articol", color=col) if it else ""

    cmp_rows = [("Google Scholar (1)", h_gs, h_gs_ns_est), ("Web of Science (2)", wos["h_index"], wos["h_index_fara_autocitari"]),
                ("Scopus (3)", sco["h_index"], sco["h_index_fara_autocitari"]),
                ("ResearchGate (B)", rg["h_index"], rg["h_index_fara_autocitari"]),
                ("OpenAlex (suplimentar)", h_oa, h_oa_ns)]
    charts["cmp"] = svg_compare(cmp_rows, "Fig. 4 – h-index pentru cazul N = 27 în cele 4(+1) variante")

    gs_rows = "".join(
        f'<tr class="{"core" if i < h_gs else ""}"><td>{i+1}</td><td>{esc(p["t"])}</td><td>{esc(p["y"])}</td>'
        f'<td class="n">{p["c"]}</td><td class="n">{s or ""}</td><td class="n">{p["c"]-s}</td>'
        f'<td class="n">{"✔" if p["c"] >= i+1 else ""}</td></tr>'
        for i, (p, (_, s)) in enumerate(zip(gs, gs_items)))
    oa_sorted = sorted(oa, key=lambda w: -w["cited"])
    oa_rows = "".join(
        f'<tr class="{"core" if i < h_oa else ""}"><td>{i+1}</td><td>{esc(w["title"])}</td><td>{w["year"]}</td>'
        f'<td class="n">{w["cited"]}</td><td class="n">{w["self"] or ""}</td><td class="n">{w["cited"]-w["self"]}</td></tr>'
        for i, w in enumerate(oa_sorted))

    rgs = st["rg"]
    contrib = "".join(f"<li>{esc(c)}</li>" for c in st["contributii_introduse"])

    with open(os.path.join(ROOT, "template.html"), encoding="utf-8") as f:
        tpl = f.read()
    subs = dict(
        DATA=DATA_COLECTARE, AZI=date.today().strftime("%d.%m.%Y"), NUME=esc(st["nume"]), PROGRAM=esc(st["program"]),
        GS_URL=GS_URL, ORCID_N=ORCID_N, SCOPUS_N=SCOPUS_N, OPENALEX_N=OPENALEX_N, RG_N=RG_N,
        GS_CIT=GS_STATS["citari"][0], GS_CIT5=GS_STATS["citari"][1], GS_H=GS_STATS["h"][0], GS_H5=GS_STATS["h"][1],
        GS_I10=GS_STATS["i10"][0], GS_I105=GS_STATS["i10"][1], GS_NART=len(gs), GS_HCALC=h_gs, GS_HNS=h_gs_ns_est,
        GS_AVG=f"{sum(gs_c)/len(gs):.1f}".replace(".", ","), GS_SUM=sum(gs_c),
        OA_N=len(oa), OA_TOT=oa_tot, OA_SELF=oa_self, OA_SELFP=f"{100*oa_self/oa_tot:.1f}".replace(".", ","),
        OA_H=h_oa, OA_HNS=h_oa_ns, OA_I10=i10([c for c, _ in oa_items]),
        WOS_H=val(wos["h_index"]), WOS_HNS=val(wos["h_index_fara_autocitari"]), WOS_DOC=val(wos["documente"]),
        WOS_CIT=val(wos["citari_total"]), WOS_CITNS=val(wos["citari_fara_autocitari"]),
        SCO_H=val(sco["h_index"]), SCO_HNS=val(sco["h_index_fara_autocitari"]), SCO_DOC=val(sco["documente"]),
        SCO_CIT=val(sco["citari_total"]), SCO_CITNS=val(sco["citari_fara_autocitari"]),
        RG_H=val(rg["h_index"]), RG_HNS=val(rg["h_index_fara_autocitari"]), RG_PUB=val(rg["publicatii"]),
        RG_CIT=val(rg["citari_total"]), RG_READ=val(rg["citiri"]), RG_RI=val(rg["research_interest"]), RG_SCORE=val(rg["rg_score"]),
        ST_GS=val(st["google_scholar_url"]), ST_ORCID=val(st["orcid_id"]), ST_RG=val(st["researchgate_url"]),
        ST_PUBLONS=val(st["publons_researcherid"]), ST_SCOPUS=val(st["scopus_author_id"] or None),
        ST_WOS=val(st["wos_researcherid"]), ST_EMAIL=val(st["email_upb"]),
        ST_RG_PUB=val(rgs["publicatii"]), ST_RG_READ=val(rgs["citiri"]), ST_RG_CIT=val(rgs["citari"]),
        ST_RG_REC=val(rgs["recomandari"]), ST_RG_FOL=val(rgs["urmaritori"]), ST_RG_FOLW=val(rgs["urmariti"]),
        ST_RG_QA=val(rgs["intrebari_raspunsuri"]), ST_RG_RI=val(rgs["research_interest"]), ST_RG_SCORE=val(rgs["rg_score"]),
        CONTRIB=contrib, GS_ROWS=gs_rows, OA_ROWS=oa_rows,
        CH_GS=charts["gs"], CH_OA=charts["oa"], CH_YEARS=charts["years"], CH_CMP=charts["cmp"],
        CH_WOS=(charts["wos"] or shot("n_wos_citation_report.png", "WoS – profilul de cercetător Bogdan C Florea (ResearcherID U-3645-2017)",
                                    "Author search → Citation report; bifați „Exclude self-citations”; notați h-index în ambele variante."))
               + shot("n_wos_dashboard.png", "WoS – Metrics Dashboard: publicații și citări pe ani", ""),
        CH_SCO=charts["sco"] or shot("n_scopus_author.png", f"Scopus – profilul autorului (Author ID {SCOPUS_N})",
                                    "Author details → Citation overview → „Exclude self citations of all authors”."),
        CH_RG=charts["rg"] or shot("n_researchgate_stats.png", "ResearchGate – Stats / h-index pentru conf. Bogdan Cristian Florea",
                                  "Profil → Stats: Research Interest, citări, citiri, h-index (cu/fără autocitări)."),
    )
    for name in ["a_google_scholar", "a_wos", "a_scopus", "a_orcid", "a_researchgate_profile", "a_researchgate_stats",
                 "a_publons", "a_rg_conectare_n", "n_google_scholar"]:
        subs["SHOT_" + name.upper()] = shot(name + ".png", *SHOT_TEXT[name])
    for k, v in subs.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    out = os.path.join(ROOT, "report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(tpl)
    print("scris", out)
    return out


SHOT_TEXT = {
    "a_google_scholar": ("Google Scholar – profilul personal", "Profil creat cu contul Google; afișează Citations / h-index / i10-index (0 dacă nu există lucrări indexate)."),
    "a_wos": ("Web of Science – căutare după autor (Miloiu C.)", "Rezultatul căutării de sine din WoS (de pe rețeaua UPB sau E-nformation)."),
    "a_scopus": ("Scopus – căutare după autor (Miloiu)", "Rezultatul Author search din Scopus; dacă nu există profil, captura cu „No results”."),
    "a_orcid": ("ORCiD – profilul personal cu ORCiD iD", "Pagina publică orcid.org/<ID> cu Employment, Education, Works, Funding etc."),
    "a_researchgate_profile": ("ResearchGate – profilul personal", "Pagina de profil cu contribuțiile introduse (proiecte, lucrare de licență etc.)."),
    "a_researchgate_stats": ("ResearchGate – Stats (după 2–3 săptămâni)", "Research Interest, citiri, citări, recomandări, urmăritori; raportul săptămânal RG."),
    "a_publons": ("Publons / Web of Science Researcher Profile", "Profilul cu ResearcherID, conectat la ORCiD."),
    "a_rg_conectare_n": ("ResearchGate – urmărirea cercetătorului N = 27", "Butonul „Following” pe profilul conf. Bogdan Cristian Florea."),
    "n_google_scholar": ("Google Scholar – profilul conf. Bogdan Cristian Florea", "Tabelul „Cited by” (All / Since 2021) și graficul pe ani."),
}


def pdf(html_path):
    out = os.path.join(ROOT, "Tema_S1_N27_Miloiu_Cristi.pdf")
    if not os.path.exists(CHROME):
        print("Chrome nu a fost găsit; deschide report.html și tipărește în PDF.")
        return
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out}", "file://" + html_path], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("scris", out)


if __name__ == "__main__":
    p = build()
    if "--no-pdf" not in sys.argv:
        pdf(p)
