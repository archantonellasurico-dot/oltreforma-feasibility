
import streamlit as st
from pathlib import Path
import json, io, copy, math
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "data" / "projects.json"

st.set_page_config(
    page_title="Oltreforma | Feasibility",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Style ----------
st.markdown("""
<style>
:root{
  --ink:#20242a;
  --muted:#6f7680;
  --line:#e6e8eb;
  --panel:#f7f7f5;
  --accent:#8b7b66;
  --ok:#2f6b4f;
  --warn:#b8791f;
  --bad:#9d3a3a;
}
.block-container{padding-top:1.4rem; padding-bottom:3rem;}
h1,h2,h3{letter-spacing:-0.02em;}
.smallcaps{font-size:.74rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);}
.hero{
  border:1px solid var(--line); border-radius:18px; padding:22px 24px;
  background:linear-gradient(180deg,#fff,#fbfaf8);
  margin-bottom:14px;
}
.kpi{
  border:1px solid var(--line);border-radius:16px;padding:16px 18px;background:white;
}
.kpi .label{font-size:.78rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;}
.kpi .value{font-size:1.8rem;font-weight:650;margin-top:3px;}
.status-ok{color:var(--ok);font-weight:650}
.status-warn{color:var(--warn);font-weight:650}
.status-bad{color:var(--bad);font-weight:650}
hr{border-color:var(--line)}
div[data-testid="stMetric"]{border:1px solid var(--line);padding:12px 14px;border-radius:14px;background:#fff;}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def load_projects():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}

def save_projects(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def euro(v):
    s = f"{v:,.0f}".replace(",", ".")
    return f"€ {s}"

def fmt(v, d=1):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_project():
    return st.session_state.projects[st.session_state.current_project]

def ensure_session():
    if "projects" not in st.session_state:
        st.session_state.projects = load_projects()
    if "current_project" not in st.session_state:
        st.session_state.current_project = next(iter(st.session_state.projects), None)
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "Vista Studio"

def calc(p):
    u = p["urbanistica"]; pr = p["programma"]; m = p["mercato"]; c = p["costi"]; i = p["incentivi"]; a = p["acquisizione"]
    sup_vol_piano = max(u["sup_lorda_piano_mq"] - u["scala_ascensore_esclusi_mq_piano"], 0)
    vol_prg = u["lotto_mq"] * u["iff_mc_mq"]
    vol_proj = sup_vol_piano * u["piani_residenziali"] * u["altezza_urbanistica_m"]
    itaca = i["itaca_pct"] if i["itaca_attivo"] else 0
    romani = i["romani_pct"] if i["romani_attivo"] else 0
    vol_inc = vol_prg * (1 + (itaca + romani) / 100)

    lavori = sum(c[k] for k in [
        "demolizione","strutture","opere_edili","impianti","finiture","serramenti",
        "ascensore","fotovoltaico","marciapiede","allacci"
    ])
    tecniche = lavori * c["spese_tecniche_pct"]/100
    imprevisti = lavori * c["imprevisti_pct"]/100
    sviluppo = lavori + tecniche + imprevisti + c["oneri"]

    out = {
        "sup_vol_piano": sup_vol_piano, "vol_prg": vol_prg, "vol_proj": vol_proj,
        "vol_inc": vol_inc, "bonus_pct": itaca+romani, "lavori": lavori,
        "tecniche": tecniche, "imprevisti": imprevisti, "sviluppo": sviluppo,
        "scenari": {}
    }
    for s in ["prudente","probabile","ottimistico"]:
        ric_res = pr["sup_commerciale_residenziale_mq"] * m[f"prezzo_mq_{s}"]
        ric_box = pr["box"] * m[f"box_{s}"]
        ricavi = ric_res + ric_box
        permuta = ricavi * a["permuta_pct"]/100 if a["modalita"] in ["Permuta","Mista"] else 0
        cash = a["prezzo_acquisto"] if a["modalita"]=="Acquisto" else (a["cash_mista"] if a["modalita"]=="Mista" else 0)
        inv = sviluppo + cash
        utile = ricavi - sviluppo - cash - permuta
        margine = (utile/ricavi*100) if ricavi else 0
        max_acq = ricavi*(1-a["target_margin_pct"]/100)-sviluppo
        max_perm_pct = max(0, min(100, max_acq/ricavi*100)) if ricavi else 0
        out["scenari"][s] = {
            "ric_res":ric_res,"ric_box":ric_box,"ricavi":ricavi,"permuta":permuta,
            "cash":cash,"investimento":inv,"utile":utile,"margine":margine,
            "max_acq":max_acq,"max_perm_pct":max_perm_pct
        }
    return out

def judgement(margin, target):
    if margin >= target:
        return "CONVENIENTE", "ok"
    if margin >= target - 4:
        return "DA NEGOZIARE", "warn"
    return "NON CONVENIENTE", "bad"

def make_pdf(p, r, client_view=True):
    bio = io.BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    W,H=A4
    def txt(x,y,t,size=10,bold=False,col=colors.HexColor("#20242a")):
        c.setFillColor(col); c.setFont("Helvetica-Bold" if bold else "Helvetica", size); c.drawString(x,y,str(t))
    y=H-55
    txt(45,y,"OLTREFORMA | FEASIBILITY",15,True); y-=24
    txt(45,y,p["meta"]["name"],18,True); y-=18
    txt(45,y,f'{p["meta"]["comune"]} · {p["meta"]["zona"]} · {p["meta"]["tipologia_intervento"]}',9,col=colors.HexColor("#6f7680")); y-=28
    c.setStrokeColor(colors.HexColor("#e6e8eb")); c.line(45,y,W-45,y); y-=26

    txt(45,y,"Sintesi urbanistica",11,True); y-=18
    txt(55,y,f'Lotto: {fmt(p["urbanistica"]["lotto_mq"])} m²  |  Iff: {fmt(p["urbanistica"]["iff_mc_mq"])} mc/m²'); y-=15
    txt(55,y,f'Volume ordinario: {fmt(r["vol_prg"],0)} m³  |  Volume progetto: {fmt(r["vol_proj"],0)} m³'); y-=15
    txt(55,y,f'Volume incentivato teorico: {fmt(r["vol_inc"],0)} m³  |  Bonus scenario: {fmt(r["bonus_pct"])}%'); y-=26

    txt(45,y,"Scenario probabile",11,True); y-=18
    s=r["scenari"]["probabile"]
    txt(55,y,f'Valore commerciale: {euro(s["ricavi"])}'); y-=15
    txt(55,y,f'Costo sviluppo prima acquisizione: {euro(r["sviluppo"])}'); y-=15
    txt(55,y,f'Utile stimato: {euro(s["utile"])}'); y-=15
    txt(55,y,f'Margine: {fmt(s["margine"])}%'); y-=15
    txt(55,y,f'Prezzo massimo sostenibile acquisizione: {euro(s["max_acq"])}'); y-=15
    txt(55,y,f'Permuta di riferimento: {fmt(p["acquisizione"]["permuta_pct"])}%'); y-=28

    j,_=judgement(s["margine"],p["acquisizione"]["target_margin_pct"])
    txt(45,y,f'Esito: {j}',14,True); y-=30
    txt(45,y,"Note",10,True); y-=16
    note = ("Le premialità volumetriche sono trattate come scenario di verifica. "
            "La loro effettiva utilizzabilità deve essere confermata rispetto alla disciplina urbanistica e normativa vigente.")
    for line in [note[i:i+90] for i in range(0,len(note),90)]:
        txt(55,y,line,8); y-=12

    c.setFillColor(colors.HexColor("#6f7680")); c.setFont("Helvetica",7)
    c.drawString(45,28,"Documento preliminare di fattibilità. Non sostituisce verifiche urbanistiche, fiscali, strutturali o estimative.")
    c.save()
    bio.seek(0)
    return bio.getvalue()

ensure_session()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('<div class="smallcaps">Oltreforma</div>', unsafe_allow_html=True)
    st.markdown("## Feasibility")
    st.caption("Valutazione preliminare immobiliare")

    names=list(st.session_state.projects.keys())
    if names:
        idx = names.index(st.session_state.current_project) if st.session_state.current_project in names else 0
        chosen = st.selectbox("Progetto", names, index=idx)
        st.session_state.current_project = chosen

    st.session_state.view_mode = st.radio("Vista", ["Vista Studio","Vista Cliente / Impresa"], horizontal=False)

    st.divider()
    new_name=st.text_input("Nuovo progetto", placeholder="Es. Via Roma")
    if st.button("＋ Crea progetto", use_container_width=True):
        if new_name.strip():
            template=copy.deepcopy(get_project())
            template["meta"]["name"]=new_name.strip()
            template["meta"]["indirizzo"]=new_name.strip()
            st.session_state.projects[new_name.strip()]=template
            st.session_state.current_project=new_name.strip()
            save_projects(st.session_state.projects)
            st.rerun()

    if st.button("Duplica progetto", use_container_width=True) and st.session_state.current_project:
        base=st.session_state.current_project
        n=f"{base} - copia"
        k=2
        while n in st.session_state.projects:
            n=f"{base} - copia {k}"; k+=1
        st.session_state.projects[n]=copy.deepcopy(get_project())
        st.session_state.projects[n]["meta"]["name"]=n
        save_projects(st.session_state.projects)
        st.session_state.current_project=n
        st.rerun()

if not st.session_state.current_project:
    st.info("Crea il primo progetto dalla barra laterale.")
    st.stop()

p=get_project()
r=calc(p)

# ---------- Header ----------
st.markdown(f"""
<div class="hero">
<div class="smallcaps">{p["meta"]["comune"]} · Zona {p["meta"]["zona"]}</div>
<div style="font-size:2rem;font-weight:700;margin-top:4px">{p["meta"]["name"]}</div>
<div style="color:#6f7680;margin-top:4px">{p["meta"]["tipologia_intervento"]}</div>
</div>
""", unsafe_allow_html=True)

prob=r["scenari"]["probabile"]
j,jc=judgement(prob["margine"],p["acquisizione"]["target_margin_pct"])
k1,k2,k3,k4=st.columns(4)
k1.metric("Valore probabile", euro(prob["ricavi"]))
k2.metric("Costo sviluppo", euro(r["sviluppo"]))
k3.metric("Margine probabile", f'{fmt(prob["margine"])}%')
k4.markdown(f'<div class="kpi"><div class="label">Esito</div><div class="value status-{jc}">{j}</div></div>', unsafe_allow_html=True)

# Client view: compact
if st.session_state.view_mode=="Vista Cliente / Impresa":
    st.markdown("### Sintesi operazione")
    c1,c2,c3=st.columns(3)
    c1.metric("Alloggi", p["programma"]["alloggi"])
    c2.metric("Box", p["programma"]["box"])
    c3.metric("Prezzo massimo sostenibile", euro(prob["max_acq"]))

    st.markdown("### Tre scenari")
    cols=st.columns(3)
    for col,s,label in zip(cols,["prudente","probabile","ottimistico"],["Prudente","Probabile","Ottimistico"]):
        x=r["scenari"][s]
        with col:
            st.markdown(f"**{label}**")
            st.metric("Valore commerciale", euro(x["ricavi"]))
            st.metric("Margine", f'{fmt(x["margine"])}%')
            st.metric("Max acquisizione", euro(x["max_acq"]))

    st.markdown("### Urbanistica")
    if r["vol_proj"]<=r["vol_prg"]:
        st.success(f'Il volume di progetto ({fmt(r["vol_proj"],0)} m³) rientra nel volume ordinario.')
    elif r["vol_proj"]<=r["vol_inc"]:
        st.warning(f'Il progetto rientra solo nello scenario incentivato teorico: {fmt(r["vol_proj"],0)} m³ su {fmt(r["vol_inc"],0)} m³.')
    else:
        st.error("Il progetto supera anche lo scenario incentivato teorico.")

    pdf=make_pdf(p,r,client_view=True)
    st.download_button("Scarica report PDF", data=pdf, file_name=f'{p["meta"]["name"]}_fattibilita.pdf', mime="application/pdf")
    st.stop()

# ---------- Studio tabs ----------
tabs=st.tabs(["Dashboard","Immobile","Urbanistica","Progetto","Costi","Mercato","Incentivi","Acquisizione / Permuta","Report"])

with tabs[0]:
    st.markdown("### Dashboard Studio")
    st.caption("Controllo sintetico economico, urbanistico e negoziale.")
    a,b,c=st.columns(3)
    a.metric("Volume ordinario", f'{fmt(r["vol_prg"],0)} m³')
    b.metric("Volume progetto", f'{fmt(r["vol_proj"],0)} m³')
    c.metric("Volume incentivato teorico", f'{fmt(r["vol_inc"],0)} m³')

    st.markdown("#### Scenari economici")
    rows=[]
    for s,label in [("prudente","Prudente"),("probabile","Probabile"),("ottimistico","Ottimistico")]:
        x=r["scenari"][s]
        rows.append({
            "Scenario":label,
            "Valore commerciale":euro(x["ricavi"]),
            "Utile":euro(x["utile"]),
            "Margine":f'{fmt(x["margine"])}%',
            "Max acquisizione":euro(x["max_acq"]),
            "Permuta max teorica":f'{fmt(x["max_perm_pct"])}%'
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

with tabs[1]:
    st.markdown("### Immobile")
    c1,c2=st.columns(2)
    with c1:
        p["meta"]["name"]=st.text_input("Nome progetto",p["meta"]["name"])
        p["meta"]["comune"]=st.text_input("Comune",p["meta"]["comune"])
        p["meta"]["indirizzo"]=st.text_input("Indirizzo",p["meta"]["indirizzo"])
    with c2:
        p["meta"]["zona"]=st.text_input("Zona urbanistica",p["meta"]["zona"])
        p["meta"]["tipologia_intervento"]=st.selectbox("Intervento",["Demolizione + ricostruzione","Nuova costruzione","Ristrutturazione"],index=["Demolizione + ricostruzione","Nuova costruzione","Ristrutturazione"].index(p["meta"]["tipologia_intervento"]) if p["meta"]["tipologia_intervento"] in ["Demolizione + ricostruzione","Nuova costruzione","Ristrutturazione"] else 0)
        p["meta"]["note"]=st.text_area("Note",p["meta"].get("note",""))

with tabs[2]:
    st.markdown("### Urbanistica")
    u=p["urbanistica"]
    c1,c2,c3=st.columns(3)
    with c1:
        u["lotto_mq"]=st.number_input("Lotto (m²)",0.0,value=float(u["lotto_mq"]),step=1.0)
        u["iff_mc_mq"]=st.number_input("Iff (mc/m²)",0.0,value=float(u["iff_mc_mq"]),step=.1)
        u["h_max_m"]=st.number_input("H max (m)",0.0,value=float(u["h_max_m"]),step=.1)
    with c2:
        u["piani_residenziali"]=st.number_input("Piani residenziali",1,value=int(u["piani_residenziali"]),step=1)
        u["sup_lorda_piano_mq"]=st.number_input("Sup. lorda/piano (m²)",0.0,value=float(u["sup_lorda_piano_mq"]),step=1.0)
        u["altezza_urbanistica_m"]=st.number_input("Altezza urbanistica/piano (m)",0.0,value=float(u["altezza_urbanistica_m"]),step=.05)
    with c3:
        u["scala_ascensore_esclusi_mq_piano"]=st.number_input("Scala/ascensore esclusi (m²/piano)",0.0,value=float(u["scala_ascensore_esclusi_mq_piano"]),step=1.0)
        u["sup_coperta_preliminare_mq"]=st.number_input("Sup. coperta preesistente (m²)",0.0,value=float(u["sup_coperta_preliminare_mq"]),step=1.0)
        u["pt_escluso_da_volume"]=st.checkbox("PT escluso dalla volumetria",value=bool(u["pt_escluso_da_volume"]))

    rr=calc(p)
    x1,x2,x3,x4=st.columns(4)
    x1.metric("Sup. volumetrica/piano",f'{fmt(rr["sup_vol_piano"])} m²')
    x2.metric("Volume PRG",f'{fmt(rr["vol_prg"],0)} m³')
    x3.metric("Volume progetto",f'{fmt(rr["vol_proj"],0)} m³')
    x4.metric("Scarto ordinario",f'{fmt(rr["vol_prg"]-rr["vol_proj"],0)} m³')

with tabs[3]:
    st.markdown("### Programma edilizio")
    pr=p["programma"]
    c1,c2,c3=st.columns(3)
    with c1:
        pr["alloggi"]=st.number_input("Alloggi",1,value=int(pr["alloggi"]))
        pr["box"]=st.number_input("Box",0,value=int(pr["box"]))
    with c2:
        pr["sup_commerciale_residenziale_mq"]=st.number_input("Sup. commerciale residenziale (m²)",0.0,value=float(pr["sup_commerciale_residenziale_mq"]),step=1.0)
        pr["balconi_fisici_mq"]=st.number_input("Balconi fisici (m²)",0.0,value=float(pr["balconi_fisici_mq"]),step=1.0)
    with c3:
        pr["box_mq_totali"]=st.number_input("Box totali (m²)",0.0,value=float(pr["box_mq_totali"]),step=1.0)
        pr["qualita"]=st.selectbox("Qualità",["Economico","Medio","Medio-alto","Alto"],index=["Economico","Medio","Medio-alto","Alto"].index(pr["qualita"]) if pr["qualita"] in ["Economico","Medio","Medio-alto","Alto"] else 1)

with tabs[4]:
    st.markdown("### Costi")
    c=p["costi"]
    fields=[
        ("demolizione","Demolizione"),("strutture","Fondazioni + strutture"),
        ("opere_edili","Opere edili"),("impianti","Impianti"),("finiture","Finiture"),
        ("serramenti","Serramenti"),("ascensore","Ascensore"),("fotovoltaico","Fotovoltaico"),
        ("marciapiede","Marciapiede"),("allacci","Allacci")
    ]
    cols=st.columns(2)
    for idx,(k,label) in enumerate(fields):
        with cols[idx%2]:
            c[k]=st.number_input(f"{label} (€)",0.0,value=float(c[k]),step=1000.0,key=f"cost_{k}")
    c1,c2,c3=st.columns(3)
    c["spese_tecniche_pct"]=c1.number_input("Spese tecniche (%)",0.0,value=float(c["spese_tecniche_pct"]),step=.5)
    c["imprevisti_pct"]=c2.number_input("Imprevisti (%)",0.0,value=float(c["imprevisti_pct"]),step=.5)
    c["oneri"]=c3.number_input("Oneri / contributi (€)",0.0,value=float(c["oneri"]),step=500.0)
    rr=calc(p)
    st.metric("Costo sviluppo prima dell'acquisizione",euro(rr["sviluppo"]))

with tabs[5]:
    st.markdown("### Mercato")
    m=p["mercato"]
    st.caption("Tre scenari modificabili.")
    data=[]
    for s,label in [("prudente","Prudente"),("probabile","Probabile"),("ottimistico","Ottimistico")]:
        c1,c2,c3=st.columns([1.2,1,1])
        c1.markdown(f"**{label}**")
        m[f"prezzo_mq_{s}"]=c2.number_input(f"€/m² {label}",0.0,value=float(m[f"prezzo_mq_{s}"]),step=50.0,key=f"pmq_{s}")
        m[f"box_{s}"]=c3.number_input(f"Box € {label}",0.0,value=float(m[f"box_{s}"]),step=500.0,key=f"box_{s}")
    rr=calc(p)
    st.dataframe([
        {"Scenario":"Prudente","Valore":euro(rr["scenari"]["prudente"]["ricavi"])},
        {"Scenario":"Probabile","Valore":euro(rr["scenari"]["probabile"]["ricavi"])},
        {"Scenario":"Ottimistico","Valore":euro(rr["scenari"]["ottimistico"]["ricavi"])}
    ],hide_index=True,use_container_width=True)

with tabs[6]:
    st.markdown("### Incentivi e premialità")
    i=p["incentivi"]
    c1,c2=st.columns(2)
    with c1:
        i["itaca_attivo"]=st.checkbox("ITACA attivo",value=bool(i["itaca_attivo"]))
        i["itaca_pct"]=st.number_input("Bonus ITACA (%)",0.0,value=float(i["itaca_pct"]),step=.5)
        i["itaca_stato"]=st.selectbox("Stato ITACA",["Verificato","Da verificare oltre densità ordinaria","Non applicabile"],index=["Verificato","Da verificare oltre densità ordinaria","Non applicabile"].index(i["itaca_stato"]) if i["itaca_stato"] in ["Verificato","Da verificare oltre densità ordinaria","Non applicabile"] else 1)
    with c2:
        i["romani_attivo"]=st.checkbox("Decreto Romani attivo",value=bool(i["romani_attivo"]))
        i["romani_pct"]=st.number_input("Bonus Romani (%)",0.0,value=float(i["romani_pct"]),step=.5)
        i["romani_stato"]=st.selectbox("Stato Romani",["Verificato","Da verificare cumulabilità/applicabilità","Non applicabile"],index=["Verificato","Da verificare cumulabilità/applicabilità","Non applicabile"].index(i["romani_stato"]) if i["romani_stato"] in ["Verificato","Da verificare cumulabilità/applicabilità","Non applicabile"] else 1)
    rr=calc(p)
    st.warning(i["nota"])
    a,b,c=st.columns(3)
    a.metric("Bonus teorico",f'{fmt(rr["bonus_pct"])}%')
    b.metric("Volume incentivato teorico",f'{fmt(rr["vol_inc"],0)} m³')
    c.metric("Margine vs progetto",f'{fmt(rr["vol_inc"]-rr["vol_proj"],0)} m³')

with tabs[7]:
    st.markdown("### Acquisizione / Permuta")
    a=p["acquisizione"]
    a["modalita"]=st.selectbox("Modalità",["Acquisto","Permuta","Mista"],index=["Acquisto","Permuta","Mista"].index(a["modalita"]))
    c1,c2,c3=st.columns(3)
    a["prezzo_acquisto"]=c1.number_input("Prezzo acquisto (€)",0.0,value=float(a["prezzo_acquisto"]),step=5000.0)
    a["permuta_pct"]=c2.slider("Permuta (% valore realizzato)",0.0,40.0,float(a["permuta_pct"]),.5)
    a["cash_mista"]=c3.number_input("Cash in modalità mista (€)",0.0,value=float(a["cash_mista"]),step=5000.0)
    a["target_margin_pct"]=st.number_input("Margine obiettivo (%)",0.0,50.0,float(a["target_margin_pct"]),.5)
    rr=calc(p); s=rr["scenari"]["probabile"]
    c1,c2,c3=st.columns(3)
    c1.metric("Permuta probabile",euro(s["permuta"]))
    c2.metric("Max acquisizione sostenibile",euro(s["max_acq"]))
    c3.metric("Permuta max teorica",f'{fmt(s["max_perm_pct"])}%')

with tabs[8]:
    st.markdown("### Report")
    rr=calc(p)
    pdf=make_pdf(p,rr,client_view=False)
    st.download_button("Genera report PDF",data=pdf,file_name=f'{p["meta"]["name"]}_fattibilita.pdf',mime="application/pdf",use_container_width=True)
    raw=json.dumps(p,ensure_ascii=False,indent=2).encode("utf-8")
    st.download_button("Esporta progetto JSON",data=raw,file_name=f'{p["meta"]["name"]}.json',mime="application/json",use_container_width=True)

# ---------- persist ----------
st.session_state.projects[st.session_state.current_project]=p
save_projects(st.session_state.projects)
