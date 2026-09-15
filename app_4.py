import streamlit as st
from pathlib import Path
import json, io, copy
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "data" / "projects.json"
SCENARIOS = [("prudente", "Prudente"), ("probabile", "Probabile"), ("ottimistico", "Ottimistico")]

st.set_page_config(
    page_title="Oltreforma | Feasibility",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Style ----------
st.markdown("""
<style>
:root{
  --ink:#20242a; --muted:#6f7680; --line:#e6e8eb; --panel:#f7f7f5;
  --accent:#8b7b66; --ok:#2f6b4f; --warn:#b8791f; --bad:#9d3a3a;
}
.block-container{padding-top:1.35rem;padding-bottom:3rem;}
h1,h2,h3{letter-spacing:-0.02em;}
.smallcaps{font-size:.74rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);}
.hero{border:1px solid var(--line);border-radius:18px;padding:22px 24px;background:linear-gradient(180deg,#fff,#fbfaf8);margin-bottom:14px;}
.kpi{border:1px solid var(--line);border-radius:16px;padding:16px 18px;background:white;min-height:112px;}
.kpi .label{font-size:.78rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;}
.kpi .value{font-size:1.55rem;font-weight:650;margin-top:5px;}
.status-ok{color:var(--ok);font-weight:650}.status-warn{color:var(--warn);font-weight:650}.status-bad{color:var(--bad);font-weight:650}
.note{border-left:3px solid var(--accent);padding:10px 14px;background:#fbfaf8;border-radius:8px;color:var(--muted);}
hr{border-color:var(--line)}
div[data-testid="stMetric"]{border:1px solid var(--line);padding:12px 14px;border-radius:14px;background:#fff;}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def load_projects():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_projects(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def euro(v):
    try:
        s = f"{float(v):,.0f}".replace(",", ".")
    except Exception:
        s = "0"
    return f"€ {s}"


def fmt(v, d=1):
    try:
        return f"{float(v):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0"


def slug(s):
    return "".join(ch if ch.isalnum() else "_" for ch in str(s))[:80]


def default_product(name="Appartamento"):
    return {
        "tipologia": name,
        "n": 1,
        "sup_media_mq": 90.0,
        "prezzo_prudente": 210000.0,
        "prezzo_probabile": 235000.0,
        "prezzo_ottimistico": 260000.0,
        "box_per_unita": 1.0,
        "note": "",
    }


def deep_defaults(target, defaults):
    """Aggiunge chiavi mancanti senza sovrascrivere i dati già presenti."""
    for k, v in defaults.items():
        if k not in target:
            target[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and isinstance(target.get(k), dict):
            deep_defaults(target[k], v)
    return target


def default_permuta_surface():
    return {
        "calcolo_attivo": True,
        "usa_superficie_manuale": False,
        "superficie_manual_mq": 0.0,
        "usa_prezzo_mq_manuale": False,
        "prezzo_mq_manuale_euro": 0.0,
        "nota": "Superficie equivalente commerciale; se la permuta individua unità precise prevale la superficie effettiva."
    }


def default_tax_reliefs():
    """Archivio parametrico 2026. Le aliquote restano modificabili dall'utente."""
    return {
        "anno_riferimento": 2026,
        "abitazione_principale": False,
        "titolare_proprieta_o_diritto_reale": False,
        "reddito_complessivo_euro": 0.0,
        "figli_fiscalmente_a_carico": 0,
        "applica_limite_detrazioni_over_75000": True,
        "note": (
            "Calcolo preliminare lordo. La spettanza effettiva dipende dal soggetto, dal titolo, "
            "dall'intervento, dalla capienza fiscale e dagli adempimenti richiesti."
        ),
        "detrazioni": {
            "bonus_casa": {
                "nome": "Bonus ristrutturazioni / recupero edilizio",
                "attivo": False,
                "aliquota_ordinaria_pct": 36.0,
                "aliquota_ab_principale_pct": 50.0,
                "usa_aliquota_manuale": False,
                "aliquota_manuale_pct": 36.0,
                "massimale_spesa_per_unita_euro": 96000.0,
                "spesa_prevista_euro": 0.0,
                "unita_agevolabili": 1,
                "quote_anni": 10,
                "categoria": "Ristrutturazione / manutenzione straordinaria",
                "nota": "Massimale di €96.000 per unità; verificare eventuale condivisione del plafond con altri interventi di recupero."
            },
            "ecobonus": {
                "nome": "Ecobonus / riqualificazione energetica",
                "attivo": False,
                "aliquota_ordinaria_pct": 36.0,
                "aliquota_ab_principale_pct": 50.0,
                "usa_aliquota_manuale": False,
                "aliquota_manuale_pct": 36.0,
                "massimale_spesa_per_unita_euro": 0.0,
                "spesa_prevista_euro": 0.0,
                "unita_agevolabili": 1,
                "quote_anni": 10,
                "categoria": "Efficienza energetica",
                "nota": "Il limite varia per tipologia: impostare il massimale specifico del caso. Escluse caldaie uniche a combustibili fossili."
            },
            "sismabonus_interventi": {
                "nome": "Sismabonus interventi antisismici",
                "attivo": False,
                "aliquota_ordinaria_pct": 36.0,
                "aliquota_ab_principale_pct": 50.0,
                "usa_aliquota_manuale": False,
                "aliquota_manuale_pct": 36.0,
                "massimale_spesa_per_unita_euro": 96000.0,
                "spesa_prevista_euro": 0.0,
                "unita_agevolabili": 1,
                "quote_anni": 5,
                "categoria": "Interventi antisismici",
                "zona_sismica": 0,
                "nota": "Zone 1, 2 e 3. Verificare asseverazioni, titolo edilizio e qualificazione dell'intervento."
            },
            "sismabonus_acquisti": {
                "nome": "Sismabonus acquisti · demolizione e ricostruzione",
                "attivo": False,
                "aliquota_ordinaria_pct": 36.0,
                "aliquota_ab_principale_pct": 50.0,
                "usa_aliquota_manuale": False,
                "aliquota_manuale_pct": 36.0,
                "massimale_spesa_per_unita_euro": 96000.0,
                "spesa_prevista_euro": 0.0,
                "unita_agevolabili": 1,
                "quote_anni": 5,
                "categoria": "Acquisto unità antisismiche",
                "zona_sismica": 0,
                "beneficiario": "Acquirente",
                "nota": (
                    "Per unità in edifici demoliti e ricostruiti da impresa nelle zone sismiche 1, 2 o 3. "
                    "È un vantaggio fiscale dell'acquirente, non un ricavo diretto dell'impresa."
                )
            },
            "bonus_mobili": {
                "nome": "Bonus mobili ed elettrodomestici",
                "attivo": False,
                "aliquota_pct": 50.0,
                "usa_aliquota_manuale": False,
                "aliquota_manuale_pct": 50.0,
                "massimale_spesa_per_unita_euro": 5000.0,
                "spesa_prevista_euro": 0.0,
                "unita_agevolabili": 1,
                "quote_anni": 10,
                "categoria": "Arredi collegati a recupero edilizio",
                "nota": "Collegato a un intervento di recupero edilizio; verificare data di inizio lavori e requisiti dei beni."
            },
            "barriere_bonus_casa": {
                "nome": "Eliminazione barriere architettoniche · Bonus casa",
                "attivo": False,
                "aliquota_ordinaria_pct": 36.0,
                "aliquota_ab_principale_pct": 50.0,
                "usa_aliquota_manuale": False,
                "aliquota_manuale_pct": 36.0,
                "massimale_spesa_per_unita_euro": 96000.0,
                "spesa_prevista_euro": 0.0,
                "unita_agevolabili": 1,
                "quote_anni": 10,
                "categoria": "Recupero edilizio",
                "nota": "Nel 2026 viene trattato qui nell'ambito del Bonus casa; attenzione al plafond condiviso di €96.000."
            },
            "acquisto_immobile_ristrutturato": {
                "nome": "Acquisto unità in edificio interamente ristrutturato",
                "attivo": False,
                "aliquota_ordinaria_pct": 36.0,
                "aliquota_ab_principale_pct": 50.0,
                "usa_aliquota_manuale": False,
                "aliquota_manuale_pct": 36.0,
                "massimale_spesa_per_unita_euro": 96000.0,
                "spesa_prevista_euro": 0.0,
                "unita_agevolabili": 1,
                "base_forfettaria_pct": 25.0,
                "quote_anni": 10,
                "categoria": "Acquisto da impresa/cooperativa",
                "beneficiario": "Acquirente",
                "nota": "La base è il 25% del prezzo di acquisto, entro il limite per unità. Verificare condizioni e termini di vendita."
            }
        }
    }



def default_professional_fee():
    return {
        "preset": "Lavori interni completi",
        "superficie_mq": 0.0,
        "base_lavori_manual_euro": 0.0,
        "usa_base_lavori_manuale": False,
        "sconto_pct": 0.0,
        "contributo_integrativo_attivo": True,
        "contributo_integrativo_pct": 4.0,
        "iva_attiva": True,
        "iva_pct": 22.0,
        "includi_nei_costi_sviluppo": False,
        "costi_collaboratori_euro": 0.0,
        "altri_costi_diretti_euro": 0.0,
        "prestazioni": [],
        "nota": "Preset commerciale sperimentale Oltreforma: valori liberamente modificabili, non tariffa normativa."
    }


def professional_fee_preset(name):
    # Valori iniziali puramente gestionali/commerciali e modificabili.
    presets = {
        "Lavori interni completi": [
            {"attivo": True, "nome": "Rilievo e restituzione stato di fatto", "metodo": "€/m²", "quantita": 0.0, "tariffa": 5.0},
            {"attivo": True, "nome": "Progetto distributivo", "metodo": "€/m²", "quantita": 0.0, "tariffa": 12.0},
            {"attivo": True, "nome": "Progetto architettonico esecutivo", "metodo": "€/m²", "quantita": 0.0, "tariffa": 18.0},
            {"attivo": True, "nome": "Interior / materiali e finiture", "metodo": "€/m²", "quantita": 0.0, "tariffa": 15.0},
            {"attivo": True, "nome": "Pratica edilizia", "metodo": "Forfait", "quantita": 1.0, "tariffa": 1500.0},
            {"attivo": True, "nome": "Computo metrico / capitolato", "metodo": "% lavori", "quantita": 1.0, "tariffa": 1.5},
            {"attivo": True, "nome": "Direzione lavori", "metodo": "% lavori", "quantita": 1.0, "tariffa": 4.0},
            {"attivo": False, "nome": "Contabilità / SAL", "metodo": "% lavori", "quantita": 1.0, "tariffa": 1.0},
            {"attivo": True, "nome": "Assistenza scelta materiali / fornitori", "metodo": "Forfait", "quantita": 1.0, "tariffa": 1500.0},
            {"attivo": False, "nome": "Rendering", "metodo": "€/unità", "quantita": 4.0, "tariffa": 250.0},
            {"attivo": True, "nome": "Fine lavori / chiusura pratica", "metodo": "Forfait", "quantita": 1.0, "tariffa": 600.0},
            {"attivo": False, "nome": "Aggiornamento catastale", "metodo": "Forfait", "quantita": 1.0, "tariffa": 700.0},
            {"attivo": False, "nome": "Sicurezza CSP/CSE", "metodo": "Forfait", "quantita": 1.0, "tariffa": 0.0},
        ],
        "Lavori interni parziali / restyling": [
            {"attivo": True, "nome": "Rilievo / verifica stato di fatto", "metodo": "€/m²", "quantita": 0.0, "tariffa": 4.0},
            {"attivo": True, "nome": "Progetto distributivo / restyling", "metodo": "€/m²", "quantita": 0.0, "tariffa": 10.0},
            {"attivo": True, "nome": "Materiali e finiture", "metodo": "€/m²", "quantita": 0.0, "tariffa": 10.0},
            {"attivo": False, "nome": "Pratica edilizia", "metodo": "Forfait", "quantita": 1.0, "tariffa": 1200.0},
            {"attivo": False, "nome": "Direzione lavori", "metodo": "% lavori", "quantita": 1.0, "tariffa": 4.0},
            {"attivo": False, "nome": "Rendering", "metodo": "€/unità", "quantita": 3.0, "tariffa": 250.0},
        ],
        "Ristrutturazione edilizia completa": [
            {"attivo": True, "nome": "Rilievo e restituzione", "metodo": "€/m²", "quantita": 0.0, "tariffa": 5.0},
            {"attivo": True, "nome": "Progetto architettonico", "metodo": "€/m²", "quantita": 0.0, "tariffa": 20.0},
            {"attivo": True, "nome": "Progetto esecutivo / dettagli", "metodo": "€/m²", "quantita": 0.0, "tariffa": 18.0},
            {"attivo": True, "nome": "Pratica edilizia", "metodo": "Forfait", "quantita": 1.0, "tariffa": 1800.0},
            {"attivo": True, "nome": "Computo / capitolato", "metodo": "% lavori", "quantita": 1.0, "tariffa": 1.5},
            {"attivo": True, "nome": "Direzione lavori", "metodo": "% lavori", "quantita": 1.0, "tariffa": 4.0},
            {"attivo": False, "nome": "Contabilità / SAL", "metodo": "% lavori", "quantita": 1.0, "tariffa": 1.0},
            {"attivo": False, "nome": "Sicurezza CSP/CSE", "metodo": "Forfait", "quantita": 1.0, "tariffa": 0.0},
            {"attivo": False, "nome": "Catasto", "metodo": "Forfait", "quantita": 1.0, "tariffa": 800.0},
        ],
        "Demolizione e ricostruzione / nuova costruzione": [
            {"attivo": True, "nome": "Progetto architettonico", "metodo": "€/m²", "quantita": 0.0, "tariffa": 22.0},
            {"attivo": True, "nome": "Progetto esecutivo / dettagli", "metodo": "€/m²", "quantita": 0.0, "tariffa": 18.0},
            {"attivo": True, "nome": "Pratica edilizia / titolo", "metodo": "Forfait", "quantita": 1.0, "tariffa": 2500.0},
            {"attivo": True, "nome": "Computo / capitolato", "metodo": "% lavori", "quantita": 1.0, "tariffa": 1.2},
            {"attivo": True, "nome": "Direzione lavori architettonica", "metodo": "% lavori", "quantita": 1.0, "tariffa": 3.5},
            {"attivo": False, "nome": "Contabilità / SAL", "metodo": "% lavori", "quantita": 1.0, "tariffa": 0.8},
            {"attivo": False, "nome": "Coordinamento specialisti", "metodo": "Forfait", "quantita": 1.0, "tariffa": 1500.0},
        ],
        "Solo direzione lavori": [
            {"attivo": True, "nome": "Direzione lavori", "metodo": "% lavori", "quantita": 1.0, "tariffa": 4.0},
            {"attivo": False, "nome": "Contabilità / SAL", "metodo": "% lavori", "quantita": 1.0, "tariffa": 1.0},
            {"attivo": False, "nome": "Fine lavori", "metodo": "Forfait", "quantita": 1.0, "tariffa": 600.0},
        ],
        "Personalizzato": []
    }
    return copy.deepcopy(presets.get(name, []))


def ensure_professional_fee(p):
    deep_defaults(p.setdefault("onorario_studio", {}), default_professional_fee())
    return p


def base_lavori_for_fee(p):
    o = p.get("onorario_studio", {})
    if o.get("usa_base_lavori_manuale", False):
        return float(o.get("base_lavori_manual_euro", 0) or 0)
    c = p.get("costi", {})
    if c.get("modalita_costi", "Parametrico €/m²") == "Parametrico €/m²":
        return float(c.get("superficie_costo_mq", 0) or 0) * float(c.get("costo_parametrico_mq", 0) or 0) + float(c.get("extra_parametrici", 0) or 0)
    keys = ["demolizione", "strutture", "opere_edili", "impianti", "finiture", "serramenti",
            "ascensore", "fotovoltaico", "marciapiede", "allacci", "sistemazioni_esterne", "predisposizioni_lift"]
    return sum(float(c.get(k, 0) or 0) for k in keys)


def calc_professional_fee(p):
    ensure_professional_fee(p)
    o = p["onorario_studio"]
    superficie = float(o.get("superficie_mq", 0) or 0)
    if superficie <= 0:
        superficie = float(p.get("costi", {}).get("superficie_costo_mq", 0) or total_sale_area(p) or 0)
    lavori = base_lavori_for_fee(p)
    rows, teorico = [], 0.0
    for row in o.get("prestazioni", []):
        if not row.get("attivo", False):
            continue
        metodo = row.get("metodo", "Forfait")
        qta = float(row.get("quantita", 1) or 0)
        tariffa = float(row.get("tariffa", 0) or 0)
        if metodo == "€/m²":
            base_qta = qta if qta > 0 else superficie
            valore = base_qta * tariffa
            formula = f"{fmt(base_qta,1)} m² × {euro(tariffa)}/m²"
        elif metodo == "% lavori":
            valore = lavori * tariffa / 100
            formula = f"{euro(lavori)} × {fmt(tariffa,2)}%"
        elif metodo == "€/unità":
            valore = qta * tariffa
            formula = f"{fmt(qta,0)} × {euro(tariffa)}"
        else:
            valore = qta * tariffa
            formula = f"{fmt(qta,0)} × {euro(tariffa)}"
        teorico += valore
        rows.append({"nome": row.get("nome","Prestazione"), "metodo": metodo, "formula": formula, "valore": valore})

    sconto_pct = float(o.get("sconto_pct", 0) or 0)
    sconto = teorico * sconto_pct / 100
    proposto = max(0.0, teorico - sconto)
    contributo = proposto * float(o.get("contributo_integrativo_pct", 4) or 0) / 100 if o.get("contributo_integrativo_attivo", True) else 0.0
    imponibile_iva = proposto + contributo
    iva = imponibile_iva * float(o.get("iva_pct", 22) or 0) / 100 if o.get("iva_attiva", True) else 0.0
    totale_cliente = imponibile_iva + iva
    collab = float(o.get("costi_collaboratori_euro", 0) or 0)
    altri = float(o.get("altri_costi_diretti_euro", 0) or 0)
    margine_studio = proposto - collab - altri
    euro_mq = proposto / superficie if superficie else 0.0
    incidenza = proposto / lavori * 100 if lavori else 0.0
    margine_pct = margine_studio / proposto * 100 if proposto else 0.0
    return {
        "superficie": superficie, "base_lavori": lavori, "rows": rows, "teorico": teorico,
        "sconto": sconto, "proposto": proposto, "contributo": contributo, "iva": iva,
        "totale_cliente": totale_cliente, "collaboratori": collab, "altri_costi": altri,
        "margine_studio": margine_studio, "euro_mq": euro_mq, "incidenza_pct": incidenza,
        "margine_studio_pct": margine_pct
    }


def merge_tax_relief_defaults(p):
    deep_defaults(p.setdefault("agevolazioni_fiscali", {}), default_tax_reliefs())
    deep_defaults(p.setdefault("acquisizione", {}).setdefault("permuta_superficie", {}), default_permuta_surface())
    i = p.setdefault("incentivi", {})
    i.setdefault("sismabonus_attivo", False)
    i.setdefault("sismabonus_stato", "Da verificare requisiti fiscali e tecnici")
    return p


def legacy_to_v2(p):
    """Rende i vecchi progetti V1 compatibili senza perdere i dati."""
    p = copy.deepcopy(p)
    u = p.setdefault("urbanistica", {})
    lotto = float(u.get("lotto_mq", 0))
    iff = float(u.get("iff_mc_mq", 0))
    u.setdefault("regime", "Fondiario / IED")
    u.setdefault("st_mq", lotto)
    u.setdefault("sf_mq", lotto)
    u.setdefault("ift_mc_mq", 0.0)
    u.setdefault("iff_mc_mq", iff)
    u.setdefault("rc_pct", 0.0)
    u.setdefault("piani_max", int(u.get("piani_residenziali", 3)))
    u.setdefault("standard_mq_ab", 0.0)
    u.setdefault("parcheggi_mq_mc", 0.10)
    u.setdefault("volume_approvato_m3", 0.0)
    u.setdefault("volume_progetto_diretto_m3", 0.0)
    u.setdefault("usa_volume_diretto", False)
    u.setdefault("nota_urbanistica", "")

    # Urbanistica V3.2 · fonti alternative della volumetria
    u.setdefault("fonte_volume", "Indice urbanistico")
    u.setdefault("volume_esistente_diretto_m3", 0.0)
    u.setdefault("usa_volume_esistente_diretto", True)
    u.setdefault("livelli_esistenti", [])
    u.setdefault("piano_casa_pct", 0.0)
    u.setdefault("piano_casa_tetto_m3", 0.0)
    u.setdefault("piano_casa_applicabilita_verificata", False)
    u.setdefault("piano_casa_riferimento", "")
    u.setdefault("volume_assunto_manuale_m3", 0.0)
    u.setdefault("usa_volume_assunto_manuale", False)

    pr = p.setdefault("programma", {})
    p.setdefault("analisi", {})
    p["analisi"].setdefault("modalita_ricavi", "Sintetico €/m²")
    p["analisi"].setdefault("alternativa_attiva", "Scenario base")

    # Se non esiste un mix, non lo imponiamo ai vecchi progetti: restano sul metodo sintetico.
    p.setdefault("mix_prodotti", [])
    p.setdefault("alternative", {})
    p.setdefault("permuta_opzioni", [])

    c = p.setdefault("costi", {})
    c.setdefault("sistemazioni_esterne", 0.0)
    c.setdefault("predisposizioni_lift", 0.0)
    c.setdefault("finanziamento", 0.0)
    c.setdefault("costo_sviluppo_override", 0.0)

    # Costi parametrici V3.1
    tipo_int = str(p.get("meta", {}).get("tipologia_intervento", ""))
    if "Demolizione" in tipo_int:
        tip_default, costo_default = "Demolizione + ricostruzione", 1800.0
    elif "Nuova costruzione" in tipo_int:
        tip_default, costo_default = "Nuova costruzione residenziale", 1900.0
    elif "Manutenzione" in tipo_int:
        tip_default, costo_default = "Manutenzione straordinaria leggera", 600.0
    else:
        tip_default, costo_default = "Ristrutturazione media", 950.0

    c.setdefault("modalita_costi", "Parametrico €/m²")
    c.setdefault("tipologia_costo_parametrico", tip_default)
    c.setdefault("superficie_costo_mq", float(p.get("programma", {}).get("sup_commerciale_residenziale_mq", 0) or 0))
    c.setdefault("costo_parametrico_mq", costo_default)
    c.setdefault("extra_parametrici", 0.0)

    a = p.setdefault("acquisizione", {})
    a.setdefault("modalita", "Acquisto")
    a.setdefault("prezzo_acquisto", 0.0)
    a.setdefault("permuta_pct", 0.0)
    a.setdefault("cash_mista", 0.0)
    a.setdefault("target_margin_pct", 18.0)
    a.setdefault("permuta_valore_manuale", 0.0)
    a.setdefault("usa_permuta_manuale", False)
    merge_tax_relief_defaults(p)
    ensure_professional_fee(p)
    return p


def ensure_session():
    if "projects" not in st.session_state:
        raw = load_projects()
        st.session_state.projects = {k: legacy_to_v2(v) for k, v in raw.items()}
    if "current_project" not in st.session_state:
        st.session_state.current_project = next(iter(st.session_state.projects), None)
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "Vista Studio"


def get_project():
    return st.session_state.projects[st.session_state.current_project]


def calc_urbanistica(p):
    u = p["urbanistica"]
    st_mq = float(u.get("st_mq", u.get("lotto_mq", 0)))
    sf_mq = float(u.get("sf_mq", u.get("lotto_mq", 0)))
    ift = float(u.get("ift_mc_mq", 0))
    iff = float(u.get("iff_mc_mq", 0))
    regime = u.get("regime", "Fondiario / IED")

    # 1) Volume da indice
    vol_territoriale = st_mq * ift if ift > 0 else 0.0
    vol_fondiario = sf_mq * iff if iff > 0 else 0.0
    if regime == "Convenzionato / PUE" and vol_territoriale > 0:
        vol_indice = vol_territoriale
        indice_usato = "Ift × St"
    else:
        vol_indice = vol_fondiario
        indice_usato = "Iff × Sf"

    # 2) Volume esistente legittimo: diretto oppure somma geometrica dei livelli/corpi
    livelli = u.get("livelli_esistenti", []) or []
    vol_esistente_geometrico = 0.0
    for row in livelli:
        sup = float(row.get("superficie_mq", 0) or 0)
        h = float(row.get("altezza_m", 0) or 0)
        coeff = float(row.get("coeff_volume", 1.0) or 0)
        vol_esistente_geometrico += sup * h * coeff

    if u.get("usa_volume_esistente_diretto", True):
        vol_esistente = float(u.get("volume_esistente_diretto_m3", 0) or 0)
        metodo_esistente = "Inserimento diretto"
    else:
        vol_esistente = vol_esistente_geometrico
        metodo_esistente = "Σ superficie × altezza × coefficiente"

    # 3) Piano Casa / premialità generica, sempre esplicitamente da verificare
    pc_pct = float(u.get("piano_casa_pct", 0) or 0)
    pc_tetto = float(u.get("piano_casa_tetto_m3", 0) or 0)
    pc_incremento_lordo = vol_esistente * pc_pct / 100 if vol_esistente > 0 else 0.0
    pc_incremento = min(pc_incremento_lordo, pc_tetto) if pc_tetto > 0 else pc_incremento_lordo
    vol_piano_casa = vol_esistente + pc_incremento if vol_esistente > 0 else 0.0

    # 4) Volume da titolo/progetto approvato
    vol_approvato = float(u.get("volume_approvato_m3", 0) or 0)

    # 5) Volume disponibile/assunto per la fattibilità
    fonte = u.get("fonte_volume", "Indice urbanistico")
    fonti = {
        "Indice urbanistico": vol_indice,
        "Volume esistente legittimo": vol_esistente,
        "Piano Casa / premialità": vol_piano_casa,
        "Titolo / progetto approvato": vol_approvato,
    }

    if u.get("usa_volume_assunto_manuale", False):
        vol_disponibile = float(u.get("volume_assunto_manuale_m3", 0) or 0)
        fonte_assunta = "Volume assunto manualmente"
    elif fonte == "Confronto più regimi":
        # In confronto non scegliamo automaticamente il valore più favorevole:
        # per prudenza resta 0 finché l'utente non seleziona una fonte concreta.
        vol_disponibile = 0.0
        fonte_assunta = "Da selezionare dopo confronto"
    else:
        vol_disponibile = float(fonti.get(fonte, 0) or 0)
        fonte_assunta = fonte

    # Volume di progetto
    sup_vol_piano = max(float(u.get("sup_lorda_piano_mq", 0)) - float(u.get("scala_ascensore_esclusi_mq_piano", 0)), 0)
    vol_geometrico = sup_vol_piano * int(u.get("piani_residenziali", 0)) * float(u.get("altezza_urbanistica_m", 0))
    vol_progetto = float(u.get("volume_progetto_diretto_m3", 0)) if u.get("usa_volume_diretto", False) else vol_geometrico

    # Incentivi energetici/ambientali già presenti nell'app:
    # calcolo teorico separato, senza sostituire la fonte urbanistica assunta.
    i = p.get("incentivi", {})
    itaca = float(i.get("itaca_pct", 0)) if i.get("itaca_attivo", False) else 0.0
    romani = float(i.get("romani_pct", 0)) if i.get("romani_attivo", False) else 0.0
    bonus = itaca + romani
    base_incentivi = vol_disponibile if vol_disponibile > 0 else vol_indice
    vol_incentivato = base_incentivi * (1 + bonus / 100) if base_incentivi else 0.0

    residuo = vol_disponibile - vol_progetto if vol_disponibile > 0 else 0.0

    return {
        "vol_territoriale": vol_territoriale,
        "vol_fondiario": vol_fondiario,
        "vol_ordinario": vol_indice,  # compatibilità con parti precedenti
        "vol_indice": vol_indice,
        "indice_usato": indice_usato,
        "vol_esistente": vol_esistente,
        "vol_esistente_geometrico": vol_esistente_geometrico,
        "metodo_esistente": metodo_esistente,
        "piano_casa_pct": pc_pct,
        "piano_casa_incremento": pc_incremento,
        "vol_piano_casa": vol_piano_casa,
        "vol_approvato": vol_approvato,
        "fonte_volume": fonte,
        "fonte_assunta": fonte_assunta,
        "vol_disponibile": vol_disponibile,
        "sup_vol_piano": sup_vol_piano,
        "vol_geometrico": vol_geometrico,
        "vol_progetto": vol_progetto,
        "residuo_volume": residuo,
        "bonus_pct": bonus,
        "vol_incentivato": vol_incentivato,
        "fonti_confronto": fonti,
    }


def calc_costs(p, override=0.0):
    c = p["costi"]

    if override and override > 0:
        return {
            "lavori": override, "tecniche": 0.0, "imprevisti": 0.0,
            "oneri": 0.0, "finanziamento": 0.0, "sviluppo": override,
            "override": True, "modalita": "Override"
        }

    if float(c.get("costo_sviluppo_override", 0)) > 0:
        v = float(c["costo_sviluppo_override"])
        return {
            "lavori": v, "tecniche": 0.0, "imprevisti": 0.0,
            "oneri": 0.0, "finanziamento": 0.0, "sviluppo": v,
            "override": True, "modalita": "Override"
        }

    modalita = c.get("modalita_costi", "Parametrico €/m²")

    if modalita == "Parametrico €/m²":
        superficie = float(c.get("superficie_costo_mq", 0))
        costo_mq = float(c.get("costo_parametrico_mq", 0))
        extra = float(c.get("extra_parametrici", 0))
        lavori = superficie * costo_mq + extra
    else:
        keys = [
            "demolizione", "strutture", "opere_edili", "impianti", "finiture",
            "serramenti", "ascensore", "fotovoltaico", "marciapiede", "allacci",
            "sistemazioni_esterne", "predisposizioni_lift"
        ]
        lavori = sum(float(c.get(k, 0)) for k in keys)

    if p.get("onorario_studio", {}).get("includi_nei_costi_sviluppo", False):
        tecniche = calc_professional_fee(p)["proposto"]
    else:
        tecniche = lavori * float(c.get("spese_tecniche_pct", 0)) / 100
    imprevisti = lavori * float(c.get("imprevisti_pct", 0)) / 100
    oneri = float(c.get("oneri", 0))
    finanziamento = float(c.get("finanziamento", 0))
    sviluppo = lavori + tecniche + imprevisti + oneri + finanziamento

    return {
        "lavori": lavori,
        "tecniche": tecniche,
        "imprevisti": imprevisti,
        "oneri": oneri,
        "finanziamento": finanziamento,
        "sviluppo": sviluppo,
        "override": False,
        "modalita": modalita
    }


def calc_mix_revenue(mix, scenario):
    total = 0.0
    rows = []
    for row in mix:
        n = int(row.get("n", 0))
        unit = float(row.get(f"prezzo_{scenario}", 0))
        value = n * unit
        total += value
        rows.append({"tipologia": row.get("tipologia", ""), "n": n, "unit": unit, "value": value})
    return total, rows


def calc_synthetic_revenue(p, scenario):
    pr = p["programma"]; m = p["mercato"]
    ric_res = float(pr.get("sup_commerciale_residenziale_mq", 0)) * float(m.get(f"prezzo_mq_{scenario}", 0))
    ric_box = int(pr.get("box", 0)) * float(m.get(f"box_{scenario}", 0))
    return ric_res + ric_box


def calc_project(p):
    urb = calc_urbanistica(p)
    cost = calc_costs(p)
    mode = p.get("analisi", {}).get("modalita_ricavi", "Sintetico €/m²")
    mix = p.get("mix_prodotti", [])
    a = p["acquisizione"]
    scenarios = {}
    for s, _ in SCENARIOS:
        if mode == "Mix per tipologia" and mix:
            revenue, product_rows = calc_mix_revenue(mix, s)
        else:
            revenue = calc_synthetic_revenue(p, s)
            product_rows = []

        if a.get("modalita") in ["Permuta", "Mista"]:
            if a.get("usa_permuta_manuale", False):
                permuta = float(a.get("permuta_valore_manuale", 0))
            else:
                permuta = revenue * float(a.get("permuta_pct", 0)) / 100
        else:
            permuta = 0.0
        cash = float(a.get("prezzo_acquisto", 0)) if a.get("modalita") == "Acquisto" else (float(a.get("cash_mista", 0)) if a.get("modalita") == "Mista" else 0.0)
        utile = revenue - cost["sviluppo"] - cash - permuta
        margine = utile / revenue * 100 if revenue else 0.0
        max_acq = revenue * (1 - float(a.get("target_margin_pct", 18)) / 100) - cost["sviluppo"]
        max_perm_pct = max(0, min(100, max_acq / revenue * 100)) if revenue else 0.0
        scenarios[s] = {
            "ricavi": revenue, "permuta": permuta, "cash": cash, "utile": utile, "margine": margine,
            "max_acq": max_acq, "max_perm_pct": max_perm_pct, "product_rows": product_rows,
        }
    return {"urbanistica": urb, "costi": cost, "scenari": scenarios}


def calc_alternative(alt, target_margin=18.0):
    mix = alt.get("mix_prodotti", [])
    cost = float(alt.get("costo_sviluppo", 0))
    out = {}
    for s, _ in SCENARIOS:
        revenue, _ = calc_mix_revenue(mix, s)
        residual = revenue - cost
        margin_before_land = residual / revenue * 100 if revenue else 0
        max_land = revenue * (1 - target_margin / 100) - cost
        out[s] = {"ricavi": revenue, "costo": cost, "residuo": residual, "margine_pre_land": margin_before_land, "max_land": max_land}
    return out


def judgement(margin, target):
    if margin >= target:
        return "CONVENIENTE", "ok"
    if margin >= target - 4:
        return "DA NEGOZIARE", "warn"
    return "NON CONVENIENTE", "bad"


def total_units(p):
    if p.get("analisi", {}).get("modalita_ricavi") == "Mix per tipologia" and p.get("mix_prodotti"):
        return sum(int(x.get("n", 0)) for x in p["mix_prodotti"])
    return int(p.get("programma", {}).get("alloggi", 0))


def total_sale_area(p):
    if p.get("analisi", {}).get("modalita_ricavi") == "Mix per tipologia" and p.get("mix_prodotti"):
        return sum(int(x.get("n", 0)) * float(x.get("sup_media_mq", 0)) for x in p["mix_prodotti"])
    return float(p.get("programma", {}).get("sup_commerciale_residenziale_mq", 0))


def probable_price_per_mq(p):
    """Prezzo medio probabile usato solo per tradurre la permuta in m² equivalenti."""
    mode = p.get("analisi", {}).get("modalita_ricavi", "Sintetico €/m²")
    ps = p.get("acquisizione", {}).get("permuta_superficie", {})
    if ps.get("usa_prezzo_mq_manuale", False) and float(ps.get("prezzo_mq_manuale_euro", 0)) > 0:
        return float(ps["prezzo_mq_manuale_euro"])
    if mode == "Mix per tipologia" and p.get("mix_prodotti"):
        area = total_sale_area(p)
        value, _ = calc_mix_revenue(p["mix_prodotti"], "probabile")
        return value / area if area else 0.0
    return float(p.get("mercato", {}).get("prezzo_mq_probabile", 0))


def calc_permuta_surface(p, permuta_value=None):
    a = p.get("acquisizione", {})
    ps = a.get("permuta_superficie", {})
    if a.get("modalita") not in ["Permuta", "Mista"] or not ps.get("calcolo_attivo", True):
        return {"valore": 0.0, "prezzo_mq": 0.0, "superficie_mq": 0.0, "manuale": False}
    if permuta_value is None:
        rr = calc_project(p)
        permuta_value = rr["scenari"]["probabile"]["permuta"]
    if ps.get("usa_superficie_manuale", False) and float(ps.get("superficie_manual_mq", 0)) > 0:
        mq = float(ps["superficie_manual_mq"])
        price = float(permuta_value) / mq if mq else 0.0
        return {"valore": float(permuta_value), "prezzo_mq": price, "superficie_mq": mq, "manuale": True}
    price = probable_price_per_mq(p)
    mq = float(permuta_value) / price if price else 0.0
    return {"valore": float(permuta_value), "prezzo_mq": price, "superficie_mq": mq, "manuale": False}


def calc_tax_reliefs(p):
    f = p.get("agevolazioni_fiscali", {})
    dets = f.get("detrazioni", {})
    main_home = bool(f.get("abitazione_principale", False)) and bool(f.get("titolare_proprieta_o_diritto_reale", False))
    tipo = p.get("meta", {}).get("tipologia_intervento", "")
    rows, warnings = [], []
    total = 0.0

    active_keys = [k for k, d in dets.items() if d.get("attivo", False)]
    if "sismabonus_interventi" in active_keys and "sismabonus_acquisti" in active_keys:
        warnings.append("Sismabonus interventi e Sismabonus acquisti sono alternativi sul medesimo intervento: non sommare i due benefici.")
    shared = {"bonus_casa", "sismabonus_interventi", "barriere_bonus_casa"}
    if len(shared.intersection(active_keys)) > 1:
        warnings.append("Più voci usano il plafond recupero edilizio/sismico da €96.000 per unità: verificare il massimale condiviso per evitare doppio conteggio.")

    for key, d in dets.items():
        if not d.get("attivo", False):
            continue
        if key == "sismabonus_acquisti" and "Demolizione" not in tipo:
            warnings.append("Sismabonus acquisti attivo ma il progetto non è classificato come demolizione + ricostruzione.")
        if key.startswith("sismabonus") and int(d.get("zona_sismica", 0) or 0) not in [1, 2, 3]:
            warnings.append(f'{d.get("nome","Sismabonus")}: indicare/verificare zona sismica 1, 2 o 3.')

        if d.get("usa_aliquota_manuale", False):
            rate = float(d.get("aliquota_manuale_pct", 0))
        elif "aliquota_pct" in d:
            rate = float(d.get("aliquota_pct", 0))
        else:
            rate = float(d.get("aliquota_ab_principale_pct" if main_home else "aliquota_ordinaria_pct", 0))

        units = max(int(d.get("unita_agevolabili", 1)), 1)
        raw = float(d.get("spesa_prevista_euro", 0))
        if key == "acquisto_immobile_ristrutturato":
            raw = raw * float(d.get("base_forfettaria_pct", 25)) / 100

        cap_unit = float(d.get("massimale_spesa_per_unita_euro", 0))
        cap = cap_unit * units if cap_unit > 0 else 0.0
        base = min(raw, cap) if cap > 0 else raw
        benefit = base * rate / 100
        years = max(int(d.get("quote_anni", 1)), 1)
        annual = benefit / years
        total += benefit
        rows.append({
            "key": key,
            "nome": d.get("nome", key),
            "spesa": float(d.get("spesa_prevista_euro", 0)),
            "base": base,
            "aliquota": rate,
            "beneficio": benefit,
            "anni": years,
            "quota_annua": annual,
            "beneficiario": d.get("beneficiario", "Contribuente"),
        })

    if f.get("applica_limite_detrazioni_over_75000", True) and float(f.get("reddito_complessivo_euro", 0)) > 75000 and total > 0:
        warnings.append("Reddito complessivo oltre €75.000: il totale teorico può essere ridotto dal limite complessivo alle detrazioni. Verificare il calcolo fiscale personale.")
    return {"totale_teorico": total, "rows": rows, "warnings": warnings, "main_home_rate": main_home}


def make_pdf(p, r):
    bio = io.BytesIO(); c = canvas.Canvas(bio, pagesize=A4); W, H = A4
    def txt(x, y, t, size=10, bold=False, col=colors.HexColor("#20242a")):
        c.setFillColor(col); c.setFont("Helvetica-Bold" if bold else "Helvetica", size); c.drawString(x, y, str(t))
    y = H - 55
    txt(45, y, "OLTREFORMA | FEASIBILITY V3.3", 15, True); y -= 24
    txt(45, y, p["meta"]["name"], 18, True); y -= 18
    txt(45, y, f'{p["meta"]["comune"]} · {p["meta"]["zona"]} · {p["meta"]["tipologia_intervento"]}', 9, col=colors.HexColor("#6f7680")); y -= 28
    c.setStrokeColor(colors.HexColor("#e6e8eb")); c.line(45, y, W-45, y); y -= 24

    u = r["urbanistica"]; s = r["scenari"]["probabile"]
    txt(45, y, "Sintesi urbanistica", 11, True); y -= 17
    txt(55, y, f'Regime indice: {p["urbanistica"].get("regime", "-")}  |  Zona: {p["meta"]["zona"]}'); y -= 14
    txt(55, y, f'Volume da indice ({u["indice_usato"]}): {fmt(u["vol_indice"],0)} m³  |  Esistente legittimo: {fmt(u["vol_esistente"],0)} m³'); y -= 14
    txt(55, y, f'Piano Casa/premialità teorica: {fmt(u["vol_piano_casa"],0)} m³  |  Titolo approvato: {fmt(u["vol_approvato"],0)} m³'); y -= 14
    txt(55, y, f'Volume assunto ({u["fonte_assunta"]}): {fmt(u["vol_disponibile"],0)} m³  |  Volume progetto: {fmt(u["vol_progetto"],0)} m³'); y -= 14
    if u["vol_disponibile"] > 0:
        txt(55, y, f'Residuo/eccedenza: {fmt(u["residuo_volume"],0)} m³'); y -= 14
    txt(55, y, f'Incentivi separati teorici: {fmt(u["bonus_pct"])}%  |  Volume incentivato teorico: {fmt(u["vol_incentivato"],0)} m³'); y -= 24

    txt(45, y, "Programma e mercato", 11, True); y -= 17
    txt(55, y, f'Unità: {total_units(p)}  |  Superficie privata/commerciale di riferimento: {fmt(total_sale_area(p),0)} m²'); y -= 14
    if p.get("analisi", {}).get("modalita_ricavi") == "Mix per tipologia":
        for row in p.get("mix_prodotti", []):
            txt(60, y, f'{row.get("tipologia")}: {row.get("n",0)} × {fmt(row.get("sup_media_mq",0),0)} m² · prezzo prob. {euro(row.get("prezzo_probabile",0))}', 8); y -= 12
    y -= 8

    txt(45, y, "Scenario probabile", 11, True); y -= 17
    txt(55, y, f'Valore commerciale: {euro(s["ricavi"])}'); y -= 14
    txt(55, y, f'Costo sviluppo prima acquisizione: {euro(r["costi"]["sviluppo"])}'); y -= 14
    txt(55, y, f'Utile dopo acquisizione/permuta impostata: {euro(s["utile"])}'); y -= 14
    txt(55, y, f'Margine: {fmt(s["margine"])}%  |  Max acquisizione al target: {euro(s["max_acq"])}'); y -= 14
    if p.get("acquisizione", {}).get("modalita") in ["Permuta", "Mista"]:
        ps_pdf = calc_permuta_surface(p, s["permuta"])
        txt(55, y, f'Permuta: {euro(s["permuta"])}  |  Superficie equivalente: {fmt(ps_pdf["superficie_mq"],1)} m²', 8); y -= 14
    tx_pdf = calc_tax_reliefs(p)
    if tx_pdf["rows"]:
        txt(55, y, f'Detrazioni fiscali attive · beneficio teorico contribuente/acquirente: {euro(tx_pdf["totale_teorico"])}', 8); y -= 14
    y -= 8

    fee_pdf = calc_professional_fee(p)
    if fee_pdf["teorico"] > 0:
        txt(45, y, "Onorario Studio", 11, True); y -= 17
        txt(55, y, f'Onorario teorico: {euro(fee_pdf["teorico"])}  |  Proposto: {euro(fee_pdf["proposto"])}', 8); y -= 12
        txt(55, y, f'Compenso: {fmt(fee_pdf["euro_mq"],1)} €/m²  |  Incidenza lavori: {fmt(fee_pdf["incidenza_pct"],2)}%', 8); y -= 12
        txt(55, y, f'Margine lordo studio: {euro(fee_pdf["margine_studio"])}  |  Totale fattura indicativo: {euro(fee_pdf["totale_cliente"])}', 8); y -= 16

    if p.get("alternative"):
        txt(45, y, "Confronto alternative – scenario probabile", 11, True); y -= 17
        for name, alt in p["alternative"].items():
            ar = calc_alternative(alt, float(p["acquisizione"].get("target_margin_pct", 18)))["probabile"]
            txt(55, y, f'{name}: ricavi {euro(ar["ricavi"])} · costo {euro(ar["costo"])} · residuo pre-land {euro(ar["residuo"])}', 8); y -= 12
        y -= 8

    txt(45, y, "Criteri di calcolo", 10, True); y -= 15
    txt(55, y, f'Volume indice: {u["indice_usato"]} · Volume assunto: {u["fonte_assunta"]}', 8); y -= 12
    if r["costi"].get("modalita") == "Parametrico €/m²":
        txt(55, y, f'Costi: superficie × parametro €/m² + extra + incidenze', 8); y -= 12
    else:
        txt(55, y, f'Costi: somma macro-voci + incidenze', 8); y -= 12
    txt(55, y, 'Margine = utile / ricavi × 100 · Permuta equivalente = valore permuta / €/m²', 8); y -= 18

    txt(45, y, "Nota", 10, True); y -= 15
    note = "Valutazione preliminare: urbanistica, costi, mercato, fiscalità e forma della permuta devono essere verificati prima di una proposta vincolante."
    for line in [note[i:i+92] for i in range(0, len(note), 92)]:
        txt(55, y, line, 8); y -= 12
    c.setFillColor(colors.HexColor("#6f7680")); c.setFont("Helvetica", 7)
    c.drawString(45, 28, "Oltreforma | Feasibility V3.3 · Documento preliminare, non sostitutivo di perizia o verifica urbanistica/fiscale.")
    c.save(); bio.seek(0); return bio.getvalue()


ensure_session()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('<div class="smallcaps">Oltreforma</div>', unsafe_allow_html=True)
    st.markdown("## Feasibility V3.3")
    st.caption("Fattibilità immobiliare · Studio / Impresa")
    names = list(st.session_state.projects.keys())
    if names:
        idx = names.index(st.session_state.current_project) if st.session_state.current_project in names else 0
        st.session_state.current_project = st.selectbox("Progetto", names, index=idx)
    st.session_state.view_mode = st.radio("Vista", ["Vista Studio", "Vista Cliente / Impresa"], horizontal=False)
    st.divider()
    new_name = st.text_input("Nuovo progetto", placeholder="Es. Area B3 - Via Toscani")
    if st.button("＋ Crea progetto", use_container_width=True):
        if new_name.strip() and st.session_state.current_project:
            template = copy.deepcopy(get_project())
            template["meta"]["name"] = new_name.strip(); template["meta"]["indirizzo"] = new_name.strip()
            st.session_state.projects[new_name.strip()] = template
            st.session_state.current_project = new_name.strip(); save_projects(st.session_state.projects); st.rerun()
    if st.button("Duplica progetto", use_container_width=True) and st.session_state.current_project:
        base = st.session_state.current_project; n = f"{base} - copia"; k = 2
        while n in st.session_state.projects:
            n = f"{base} - copia {k}"; k += 1
        st.session_state.projects[n] = copy.deepcopy(get_project()); st.session_state.projects[n]["meta"]["name"] = n
        st.session_state.current_project = n; save_projects(st.session_state.projects); st.rerun()

if not st.session_state.current_project:
    st.info("Crea il primo progetto dalla barra laterale."); st.stop()

p = get_project(); ensure_professional_fee(p); r = calc_project(p); prob = r["scenari"]["probabile"]

# ---------- Header ----------
st.markdown(f"""
<div class="hero">
<div class="smallcaps">{p['meta']['comune']} · Zona {p['meta']['zona']}</div>
<div style="font-size:2rem;font-weight:700;margin-top:4px">{p['meta']['name']}</div>
<div style="color:#6f7680;margin-top:4px">{p['meta']['tipologia_intervento']}</div>
</div>
""", unsafe_allow_html=True)

j, jc = judgement(prob["margine"], float(p["acquisizione"].get("target_margin_pct", 18)))
k1, k2, k3, k4 = st.columns(4)
k1.metric("Valore probabile", euro(prob["ricavi"]))
k2.metric("Costo sviluppo", euro(r["costi"]["sviluppo"]))
k3.metric("Margine probabile", f'{fmt(prob["margine"])}%')
k4.markdown(f'<div class="kpi"><div class="label">Esito</div><div class="value status-{jc}">{j}</div></div>', unsafe_allow_html=True)

# ---------- Vista Cliente / Impresa ----------
if st.session_state.view_mode == "Vista Cliente / Impresa":
    st.markdown("### Sintesi operazione")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unità", total_units(p)); c2.metric("Valore probabile", euro(prob["ricavi"]))
    c3.metric("Residuo prima del suolo", euro(prob["ricavi"] - r["costi"]["sviluppo"]))
    c4.metric("Max acquisizione al target", euro(prob["max_acq"]))

    if p.get("acquisizione", {}).get("modalita") in ["Permuta", "Mista"]:
        ps_client = calc_permuta_surface(p, prob["permuta"])
        st.markdown("### Permuta")
        pc1, pc2 = st.columns(2)
        pc1.metric("Valore riconosciuto", euro(prob["permuta"]))
        pc2.metric("Superficie equivalente", f'{fmt(ps_client["superficie_mq"],1)} m²')

    tx_client = calc_tax_reliefs(p)
    if tx_client["rows"]:
        st.markdown("### Agevolazioni fiscali attivate")
        st.metric("Beneficio fiscale teorico complessivo", euro(tx_client["totale_teorico"]))
        st.caption("Valore informativo riferito al contribuente/acquirente; non costituisce ricavo diretto dell'impresa.")

    if p.get("alternative"):
        st.markdown("### Confronto alternative")
        rows = []
        for name, alt in p["alternative"].items():
            ar = calc_alternative(alt, float(p["acquisizione"].get("target_margin_pct", 18)))["probabile"]
            rows.append({"Alternativa": name, "Ricavi": euro(ar["ricavi"]), "Costo sviluppo": euro(ar["costo"]), "Residuo pre-suolo": euro(ar["residuo"]), "Max suolo/permuta al target": euro(ar["max_land"])})
        st.dataframe(rows, hide_index=True, use_container_width=True)

    st.markdown("### Tre scenari")
    cols = st.columns(3)
    for col, (s, label) in zip(cols, SCENARIOS):
        x = r["scenari"][s]
        with col:
            st.markdown(f"**{label}**"); st.metric("Valore", euro(x["ricavi"])); st.metric("Margine", f'{fmt(x["margine"])}%'); st.metric("Max acquisizione", euro(x["max_acq"]))

    if p.get("permuta_opzioni"):
        st.markdown("### Opzioni negoziali")
        for op in p["permuta_opzioni"]:
            val = float(op.get("valore_totale", 0)); margin = (prob["ricavi"] - r["costi"]["sviluppo"] - val) / prob["ricavi"] * 100 if prob["ricavi"] else 0
            st.write(f'**{op.get("nome","Opzione")}** — {op.get("descrizione","")} · valore {euro(val)} · margine teorico {fmt(margin)}%')

    st.download_button("Scarica report PDF", data=make_pdf(p, r), file_name=f'{slug(p["meta"]["name"])}_fattibilita.pdf', mime="application/pdf")
    st.stop()

# ---------- Studio tabs ----------
tabs = st.tabs(["Dashboard", "Immobile", "Urbanistica", "Product Mix", "Costi", "Mercato", "Alternative", "Incentivi", "Detrazioni 2026", "Acquisizione / Permuta", "Onorario Studio", "Report", "Guida / Legenda"])

with tabs[0]:
    st.markdown("### Dashboard Studio")
    st.caption("Controllo economico, urbanistico e negoziale. I dati marcati come preliminari restano da verificare.")
    u = r["urbanistica"]
    a, b, c, d = st.columns(4)
    a.metric("Volume disponibile assunto", f'{fmt(u["vol_disponibile"],0)} m³' if u["vol_disponibile"] else "—")
    b.metric("Volume progetto", f'{fmt(u["vol_progetto"],0)} m³')
    c.metric("Residuo / eccedenza", f'{fmt(u["residuo_volume"],0)} m³' if u["vol_disponibile"] else "—")
    d.metric("Fonte volumetria", u["fonte_assunta"])
    with st.expander("Come è calcolata la volumetria?", expanded=False):
        st.write(f'**Indice:** {u["indice_usato"]} = {fmt(u["vol_indice"],0)} m³')
        st.write(f'**Esistente legittimo:** {u["metodo_esistente"]} = {fmt(u["vol_esistente"],0)} m³')
        st.write(f'**Piano Casa / premialità:** {fmt(u["vol_esistente"],0)} + {fmt(u["piano_casa_incremento"],0)} = {fmt(u["vol_piano_casa"],0)} m³')
        st.write(f'**Titolo/progetto approvato:** {fmt(u["vol_approvato"],0)} m³')
        st.write(f'**Volume assunto:** {u["fonte_assunta"]} = {fmt(u["vol_disponibile"],0)} m³')
        st.write(f'**Confronto col progetto:** {fmt(u["vol_disponibile"],0)} − {fmt(u["vol_progetto"],0)} = {fmt(u["residuo_volume"],0)} m³')
    st.markdown("#### Scenari economici")
    rows = []
    for s, label in SCENARIOS:
        x = r["scenari"][s]
        rows.append({"Scenario": label, "Valore commerciale": euro(x["ricavi"]), "Utile": euro(x["utile"]), "Margine": f'{fmt(x["margine"])}%', "Max acquisizione": euro(x["max_acq"]), "Permuta max teorica": f'{fmt(x["max_perm_pct"])}%'})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if p.get("alternative"):
        st.markdown("#### Alternative progettuali · scenario probabile")
        rows = []
        for name, alt in p["alternative"].items():
            ar = calc_alternative(alt, float(p["acquisizione"].get("target_margin_pct", 18)))["probabile"]
            rows.append({"Alternativa": name, "Ricavi": euro(ar["ricavi"]), "Costo": euro(ar["costo"]), "Residuo pre-suolo": euro(ar["residuo"]), "Margine pre-suolo": f'{fmt(ar["margine_pre_land"])}%', "Max suolo/permuta target": euro(ar["max_land"])})
        st.dataframe(rows, hide_index=True, use_container_width=True)

    # Sintesi permuta e agevolazioni fiscali
    rr_dash = calc_project(p)
    if p.get("acquisizione", {}).get("modalita") in ["Permuta", "Mista"]:
        ps_dash = calc_permuta_surface(p, rr_dash["scenari"]["probabile"]["permuta"])
        q1, q2, q3 = st.columns(3)
        q1.metric("Permuta · valore probabile", euro(ps_dash["valore"]))
        q2.metric("Permuta · superficie equivalente", f'{fmt(ps_dash["superficie_mq"],1)} m²')
        q3.metric("Valore €/m² usato", euro(ps_dash["prezzo_mq"]))
    tax_dash = calc_tax_reliefs(p)
    if tax_dash["rows"]:
        st.markdown("#### Agevolazioni fiscali attive · stima lorda")
        t1, t2 = st.columns(2)
        t1.metric("Benefici fiscali teorici", euro(tax_dash["totale_teorico"]))
        t2.caption("Benefici del contribuente/acquirente: non vengono sommati automaticamente ai ricavi dell'impresa.")

with tabs[1]:
    st.markdown("### Immobile")
    c1, c2 = st.columns(2)
    with c1:
        p["meta"]["name"] = st.text_input("Nome progetto", p["meta"]["name"])
        p["meta"]["comune"] = st.text_input("Comune", p["meta"]["comune"])
        p["meta"]["indirizzo"] = st.text_input("Indirizzo", p["meta"]["indirizzo"])
    with c2:
        p["meta"]["zona"] = st.text_input("Zona urbanistica", p["meta"]["zona"])
        opts = ["Demolizione + ricostruzione", "Nuova costruzione", "Ristrutturazione", "Manutenzione straordinaria"]
        cur = p["meta"].get("tipologia_intervento", opts[0]); p["meta"]["tipologia_intervento"] = st.selectbox("Intervento", opts, index=opts.index(cur) if cur in opts else 0)
        p["meta"]["note"] = st.text_area("Note", p["meta"].get("note", ""))

with tabs[2]:
    st.markdown("### Urbanistica")
    u = p["urbanistica"]
    st.caption("Qui distinguiamo il volume disponibile/ammissibile dal volume di progetto. Nessuna premialità viene considerata automaticamente come diritto acquisito.")

    # Regime dell'indice
    reg_opts = ["Fondiario / IED", "Convenzionato / PUE"]
    u["regime"] = st.selectbox(
        "Regime dell'indice urbanistico",
        reg_opts,
        index=reg_opts.index(u.get("regime")) if u.get("regime") in reg_opts else 0,
        help="Fondiario: usa Iff × Sf. Convenzionato/PUE: usa Ift × St quando l'indice territoriale è valorizzato."
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        u["st_mq"] = st.number_input("St · superficie territoriale (m²)", 0.0, value=float(u.get("st_mq", 0)), step=1.0, help="Superficie territoriale usata con l'indice Ift.")
        u["ift_mc_mq"] = st.number_input("Ift (m³/m²)", 0.0, value=float(u.get("ift_mc_mq", 0)), step=.01, help="Indice di fabbricabilità territoriale.")
        u["standard_mq_ab"] = st.number_input("Standard (m²/ab)", 0.0, value=float(u.get("standard_mq_ab", 0)), step=.5)
    with c2:
        u["sf_mq"] = st.number_input("Sf · superficie fondiaria (m²)", 0.0, value=float(u.get("sf_mq", 0)), step=1.0, help="Superficie fondiaria usata con l'indice Iff.")
        u["iff_mc_mq"] = st.number_input("Iff (m³/m²)", 0.0, value=float(u.get("iff_mc_mq", 0)), step=.01, help="Indice di fabbricabilità fondiaria.")
        u["rc_pct"] = st.number_input("Rc (%)", 0.0, 100.0, value=float(u.get("rc_pct", 0)), step=1.0, help="Rapporto di copertura.")
    with c3:
        u["h_max_m"] = st.number_input("H max (m)", 0.0, value=float(u.get("h_max_m", 0)), step=.1)
        u["piani_max"] = st.number_input("Piani max", 0, value=int(u.get("piani_max", 0)), step=1)
        u["parcheggi_mq_mc"] = st.number_input("Parcheggi privati (m²/m³)", 0.0, value=float(u.get("parcheggi_mq_mc", .1)), step=.01)
    with c4:
        u["volume_approvato_m3"] = st.number_input(
            "Volume da titolo / progetto approvato (m³)", 0.0,
            value=float(u.get("volume_approvato_m3", 0)), step=10.0,
            help="Volume già assentito o assunto da un titolo/progetto approvato. Inserire solo se documentato."
        )
        u["usa_volume_diretto"] = st.checkbox("Inserisci volume progetto diretto", value=bool(u.get("usa_volume_diretto", False)))
        if u["usa_volume_diretto"]:
            u["volume_progetto_diretto_m3"] = st.number_input("Volume progetto (m³)", 0.0, value=float(u.get("volume_progetto_diretto_m3", 0)), step=10.0)

    # Volume esistente
    with st.expander("1 · Volume esistente legittimo", expanded=True):
        u["usa_volume_esistente_diretto"] = st.radio(
            "Come vuoi determinare il volume esistente?",
            [True, False],
            index=0 if u.get("usa_volume_esistente_diretto", True) else 1,
            format_func=lambda x: "Inserimento diretto dei m³" if x else "Calcolo geometrico per livelli/corpi",
            horizontal=True
        )
        if u["usa_volume_esistente_diretto"]:
            u["volume_esistente_diretto_m3"] = st.number_input(
                "Volume esistente legittimo (m³)", 0.0,
                value=float(u.get("volume_esistente_diretto_m3", 0)), step=10.0,
                help="Inserire il volume legittimo risultante da titolo, stato legittimo o verifica urbanistica."
            )
        else:
            livelli = u.setdefault("livelli_esistenti", [])
            st.caption("Per ogni livello/corpo: volume = superficie × altezza urbanistica × coefficiente volumetrico.")
            for idx, row in enumerate(list(livelli)):
                with st.container(border=True):
                    l1, l2, l3, l4, l5 = st.columns([1.5, 1, 1, 1, .6])
                    row["nome"] = l1.text_input("Livello / corpo", row.get("nome", f"Livello {idx+1}"), key=f"urb_ex_nome_{idx}")
                    row["superficie_mq"] = l2.number_input("Superficie (m²)", 0.0, value=float(row.get("superficie_mq", 0)), step=1.0, key=f"urb_ex_sup_{idx}")
                    row["altezza_m"] = l3.number_input("Altezza (m)", 0.0, value=float(row.get("altezza_m", 0)), step=.05, key=f"urb_ex_h_{idx}")
                    row["coeff_volume"] = l4.number_input("Coeff.", 0.0, value=float(row.get("coeff_volume", 1.0)), step=.1, key=f"urb_ex_coeff_{idx}", help="1,00 se il volume è interamente computato; modificabile per casi particolari.")
                    if l5.button("Elimina", key=f"urb_ex_del_{idx}"):
                        livelli.pop(idx); st.rerun()
                    st.caption(f'Volume riga: {fmt(float(row.get("superficie_mq",0))*float(row.get("altezza_m",0))*float(row.get("coeff_volume",1)),0)} m³')
            if st.button("＋ Aggiungi livello/corpo", key="urb_add_existing"):
                livelli.append({"nome": f"Livello {len(livelli)+1}", "superficie_mq": 0.0, "altezza_m": 3.0, "coeff_volume": 1.0})
                st.rerun()

    # Piano Casa / premialità
    with st.expander("2 · Piano Casa / premialità volumetrica", expanded=True):
        pc1, pc2 = st.columns(2)
        u["piano_casa_pct"] = pc1.number_input(
            "Incremento teorico (%)", 0.0,
            value=float(u.get("piano_casa_pct", 0)), step=1.0,
            help="Percentuale applicata al volume esistente legittimo. Non implica automaticamente l'applicabilità della norma."
        )
        u["piano_casa_tetto_m3"] = pc2.number_input(
            "Tetto massimo incremento (m³) · 0 = nessun tetto", 0.0,
            value=float(u.get("piano_casa_tetto_m3", 0)), step=10.0
        )
        u["piano_casa_applicabilita_verificata"] = st.checkbox(
            "Applicabilità verificata per questo intervento",
            value=bool(u.get("piano_casa_applicabilita_verificata", False))
        )
        u["piano_casa_riferimento"] = st.text_input(
            "Norma / delibera / riferimento",
            u.get("piano_casa_riferimento", ""),
            placeholder="Es. legge regionale, delibera comunale, articolo..."
        )
        if u.get("piano_casa_pct", 0) > 0 and not u.get("piano_casa_applicabilita_verificata", False):
            st.warning("Premialità inserita ma applicabilità non verificata: il risultato resta uno scenario teorico.")

    # Fonte del volume da assumere
    st.markdown("#### 3 · Volume da assumere nella fattibilità")
    fonte_opts = [
        "Indice urbanistico",
        "Volume esistente legittimo",
        "Piano Casa / premialità",
        "Titolo / progetto approvato",
        "Confronto più regimi",
    ]
    cur_fonte = u.get("fonte_volume", "Indice urbanistico")
    u["fonte_volume"] = st.selectbox(
        "Fonte della volumetria disponibile",
        fonte_opts,
        index=fonte_opts.index(cur_fonte) if cur_fonte in fonte_opts else 0,
        help="Scegli quale fonte deve alimentare il business plan. 'Confronto più regimi' non seleziona automaticamente il valore maggiore."
    )
    u["usa_volume_assunto_manuale"] = st.checkbox(
        "Assumi manualmente un volume dopo la verifica/confronto",
        value=bool(u.get("usa_volume_assunto_manuale", False))
    )
    if u["usa_volume_assunto_manuale"]:
        u["volume_assunto_manuale_m3"] = st.number_input(
            "Volume disponibile assunto manualmente (m³)", 0.0,
            value=float(u.get("volume_assunto_manuale_m3", 0)), step=10.0,
            help="Usare quando la verifica urbanistica porta a un valore specifico che vuoi assumere nel business plan."
        )

    # Volume progetto
    with st.expander("4 · Calcolo geometrico del volume di progetto", expanded=not u.get("usa_volume_diretto", False)):
        g1, g2, g3, g4 = st.columns(4)
        u["piani_residenziali"] = g1.number_input("Piani considerati", 0, value=int(u.get("piani_residenziali", 0)), step=1)
        u["sup_lorda_piano_mq"] = g2.number_input("Sup. lorda/piano (m²)", 0.0, value=float(u.get("sup_lorda_piano_mq", 0)), step=1.0)
        u["scala_ascensore_esclusi_mq_piano"] = g3.number_input("Esclusioni/piano (m²)", 0.0, value=float(u.get("scala_ascensore_esclusi_mq_piano", 0)), step=1.0)
        u["altezza_urbanistica_m"] = g4.number_input("Altezza urbanistica (m)", 0.0, value=float(u.get("altezza_urbanistica_m", 0)), step=.05)
        u["pt_escluso_da_volume"] = st.checkbox("PT escluso dalla volumetria", value=bool(u.get("pt_escluso_da_volume", False)))
        u["sup_coperta_preliminare_mq"] = st.number_input("Sup. coperta preesistente / riferimento (m²)", 0.0, value=float(u.get("sup_coperta_preliminare_mq", 0)), step=1.0)

    u["nota_urbanistica"] = st.text_area("Nota urbanistica / verifiche aperte", u.get("nota_urbanistica", ""))

    rr = calc_project(p)
    ur = rr["urbanistica"]

    st.markdown("#### Confronto volumetrie")
    rows_urb = [
        {"Fonte": f'Indice urbanistico · {ur["indice_usato"]}', "Volume": f'{fmt(ur["vol_indice"],0)} m³', "Stato": "Calcolato dai parametri"},
        {"Fonte": "Volume esistente legittimo", "Volume": f'{fmt(ur["vol_esistente"],0)} m³', "Stato": ur["metodo_esistente"]},
        {"Fonte": "Piano Casa / premialità", "Volume": f'{fmt(ur["vol_piano_casa"],0)} m³', "Stato": "Verificato" if u.get("piano_casa_applicabilita_verificata", False) else "Da verificare"},
        {"Fonte": "Titolo / progetto approvato", "Volume": f'{fmt(ur["vol_approvato"],0)} m³', "Stato": "Inserito manualmente"},
    ]
    st.dataframe(rows_urb, hide_index=True, use_container_width=True)

    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Volume disponibile assunto", f'{fmt(ur["vol_disponibile"],0)} m³' if ur["vol_disponibile"] else "—")
    x2.metric("Volume progetto", f'{fmt(ur["vol_progetto"],0)} m³')
    if ur["vol_disponibile"]:
        x3.metric("Residuo / eccedenza", f'{fmt(ur["residuo_volume"],0)} m³')
        x4.metric("Utilizzo volume", f'{fmt((ur["vol_progetto"]/ur["vol_disponibile"]*100) if ur["vol_disponibile"] else 0)}%')
    else:
        x3.metric("Residuo / eccedenza", "—")
        x4.metric("Utilizzo volume", "—")

    with st.expander("Come sono ottenuti questi risultati?", expanded=True):
        st.markdown("**Volume da indice**")
        if u.get("regime") == "Convenzionato / PUE" and ur["vol_territoriale"] > 0:
            st.write(f'St × Ift = {fmt(u.get("st_mq",0),2)} m² × {fmt(u.get("ift_mc_mq",0),2)} m³/m² = **{fmt(ur["vol_indice"],0)} m³**')
        else:
            st.write(f'Sf × Iff = {fmt(u.get("sf_mq",0),2)} m² × {fmt(u.get("iff_mc_mq",0),2)} m³/m² = **{fmt(ur["vol_indice"],0)} m³**')

        st.markdown("**Volume esistente legittimo**")
        if u.get("usa_volume_esistente_diretto", True):
            st.write(f'Inserimento diretto = **{fmt(ur["vol_esistente"],0)} m³**')
        else:
            st.write(f'Σ (superficie × altezza × coefficiente) = **{fmt(ur["vol_esistente"],0)} m³**')

        st.markdown("**Piano Casa / premialità**")
        st.write(
            f'{fmt(ur["vol_esistente"],0)} m³ + {fmt(ur["piano_casa_pct"],2)}% '
            f'= incremento {fmt(ur["piano_casa_incremento"],0)} m³ → **{fmt(ur["vol_piano_casa"],0)} m³**'
        )
        if float(u.get("piano_casa_tetto_m3",0)) > 0:
            st.caption(f'Tetto incremento applicato: {fmt(u.get("piano_casa_tetto_m3",0),0)} m³.')

        st.markdown("**Volume di progetto**")
        if u.get("usa_volume_diretto", False):
            st.write(f'Inserimento diretto = **{fmt(ur["vol_progetto"],0)} m³**')
        else:
            st.write(
                f'({fmt(u.get("sup_lorda_piano_mq",0),2)} − {fmt(u.get("scala_ascensore_esclusi_mq_piano",0),2)}) m² '
                f'× {int(u.get("piani_residenziali",0))} piani × {fmt(u.get("altezza_urbanistica_m",0),2)} m '
                f'= **{fmt(ur["vol_progetto"],0)} m³**'
            )

        st.markdown("**Verifica finale**")
        if ur["vol_disponibile"]:
            st.write(f'{fmt(ur["vol_disponibile"],0)} − {fmt(ur["vol_progetto"],0)} = **{fmt(ur["residuo_volume"],0)} m³**')
            if ur["residuo_volume"] >= 0:
                st.success("Il volume di progetto rientra nel volume assunto per la fattibilità.")
            else:
                st.error("Il volume di progetto eccede il volume assunto per la fattibilità.")
        else:
            st.info("Seleziona una fonte concreta oppure inserisci un volume assunto manualmente per ottenere la verifica finale.")

with tabs[3]:
    st.markdown("### Product Mix")
    p["analisi"]["modalita_ricavi"] = st.radio("Metodo ricavi", ["Sintetico €/m²", "Mix per tipologia"], index=1 if p["analisi"].get("modalita_ricavi") == "Mix per tipologia" else 0, horizontal=True)
    if p["analisi"]["modalita_ricavi"] == "Sintetico €/m²":
        pr = p["programma"]; c1, c2, c3 = st.columns(3)
        pr["alloggi"] = c1.number_input("Alloggi", 1, value=int(pr.get("alloggi", 1)))
        pr["sup_commerciale_residenziale_mq"] = c2.number_input("Sup. commerciale residenziale (m²)", 0.0, value=float(pr.get("sup_commerciale_residenziale_mq", 0)), step=1.0)
        pr["box"] = c3.number_input("Box", 0, value=int(pr.get("box", 0)))
        pr["balconi_fisici_mq"] = c1.number_input("Balconi fisici (m²)", 0.0, value=float(pr.get("balconi_fisici_mq", 0)), step=1.0)
        pr["box_mq_totali"] = c2.number_input("Box totali (m²)", 0.0, value=float(pr.get("box_mq_totali", 0)), step=1.0)
    else:
        st.caption("Ogni tipologia ha quantità, superficie media e prezzo unitario per scenario. Le superfici sono di riferimento commerciale/privato e non sostituiscono il calcolo urbanistico.")
        mix = p.setdefault("mix_prodotti", [])
        for idx, row in enumerate(list(mix)):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1.6, .7, .9, .6])
                row["tipologia"] = c1.text_input("Tipologia", row.get("tipologia", ""), key=f"mix_name_{idx}")
                row["n"] = c2.number_input("N.", 0, value=int(row.get("n", 0)), step=1, key=f"mix_n_{idx}")
                row["sup_media_mq"] = c3.number_input("Sup. media (m²)", 0.0, value=float(row.get("sup_media_mq", 0)), step=5.0, key=f"mix_sup_{idx}")
                if c4.button("Elimina", key=f"mix_del_{idx}"):
                    mix.pop(idx); st.rerun()
                q1, q2, q3 = st.columns(3)
                row["prezzo_prudente"] = q1.number_input("Prezzo prudente (€)", 0.0, value=float(row.get("prezzo_prudente", 0)), step=5000.0, key=f"mix_pp_{idx}")
                row["prezzo_probabile"] = q2.number_input("Prezzo probabile (€)", 0.0, value=float(row.get("prezzo_probabile", 0)), step=5000.0, key=f"mix_pb_{idx}")
                row["prezzo_ottimistico"] = q3.number_input("Prezzo ottimistico (€)", 0.0, value=float(row.get("prezzo_ottimistico", 0)), step=5000.0, key=f"mix_po_{idx}")
                row["note"] = st.text_input("Note / pertinenze", row.get("note", ""), key=f"mix_note_{idx}")
        if st.button("＋ Aggiungi tipologia"):
            mix.append(default_product()); st.rerun()
        rr = calc_project(p)
        c1, c2, c3 = st.columns(3)
        c1.metric("Unità totali", total_units(p)); c2.metric("Superficie totale di riferimento", f'{fmt(total_sale_area(p),0)} m²'); c3.metric("Ricavi probabili", euro(rr["scenari"]["probabile"]["ricavi"]))

with tabs[4]:
    st.markdown("### Costi di sviluppo")
    c = p["costi"]
    st.caption("Per una fattibilità veloce usa il calcolo parametrico €/m². Il dettaglio resta disponibile quando hai dati più precisi.")

    c["modalita_costi"] = st.radio(
        "Metodo di calcolo costi",
        ["Parametrico €/m²", "Dettagliato"],
        index=0 if c.get("modalita_costi", "Parametrico €/m²") == "Parametrico €/m²" else 1,
        horizontal=True
    )

    c["costo_sviluppo_override"] = st.number_input(
        "Costo sviluppo diretto / override (€) · lascia 0 per usare il metodo scelto",
        0.0,
        value=float(c.get("costo_sviluppo_override", 0)),
        step=10000.0
    )

    if float(c.get("costo_sviluppo_override", 0)) > 0:
        st.warning("È attivo un costo override: finché questo valore è maggiore di 0, sostituisce tutto il calcolo parametrico/dettagliato.")

    if c["modalita_costi"] == "Parametrico €/m²":
        st.markdown("#### Screening rapido per tipologia")

        preset = {
            "Manutenzione straordinaria leggera": 600.0,
            "Ristrutturazione media": 950.0,
            "Ristrutturazione pesante": 1300.0,
            "Demolizione + ricostruzione": 1800.0,
            "Nuova costruzione residenziale": 1900.0,
            "Nuova costruzione medio-alta": 2200.0,
            "Personalizzato": float(c.get("costo_parametrico_mq", 1800.0)),
        }

        tipologie = list(preset.keys())
        cur_tip = c.get("tipologia_costo_parametrico", "Demolizione + ricostruzione")
        if cur_tip not in tipologie:
            cur_tip = "Personalizzato"

        q1, q2, q3 = st.columns(3)
        nuova_tip = q1.selectbox(
            "Tipologia / livello intervento",
            tipologie,
            index=tipologie.index(cur_tip)
        )

        if nuova_tip != c.get("tipologia_costo_parametrico"):
            c["tipologia_costo_parametrico"] = nuova_tip
            if nuova_tip != "Personalizzato":
                c["costo_parametrico_mq"] = preset[nuova_tip]

        if float(c.get("superficie_costo_mq", 0)) <= 0:
            c["superficie_costo_mq"] = total_sale_area(p)

        c["superficie_costo_mq"] = q2.number_input(
            "Superficie di riferimento (m²)",
            0.0,
            value=float(c.get("superficie_costo_mq", 0)),
            step=10.0,
            help="Superficie usata per lo screening dei costi; sostituiscila con la superficie costruita reale quando disponibile."
        )
        c["costo_parametrico_mq"] = q3.number_input(
            "Costo parametrico (€/m²)",
            0.0,
            value=float(c.get("costo_parametrico_mq", preset.get(nuova_tip, 1800.0))),
            step=50.0
        )

        c["extra_parametrici"] = st.number_input(
            "Extra non compresi nel parametro (€)",
            0.0,
            value=float(c.get("extra_parametrici", 0)),
            step=5000.0,
            help="Opere particolari, sistemazioni esterne importanti o costi eccezionali."
        )

        base_lavori = float(c.get("superficie_costo_mq", 0)) * float(c.get("costo_parametrico_mq", 0))
        p1, p2, p3 = st.columns(3)
        p1.metric("Costo base lavori", euro(base_lavori))
        p2.metric("Parametro", f'{fmt(c.get("costo_parametrico_mq",0),0)} €/m²')
        p3.metric("Superficie", f'{fmt(c.get("superficie_costo_mq",0),0)} m²')

        st.info("I valori €/m² sono parametri preliminari modificabili. Quando il progetto si consolida, vanno sostituiti o verificati con costi reali/prezzario/computo.")

    else:
        st.markdown("#### Costi dettagliati")
        fields = [
            ("demolizione", "Demolizione"),
            ("strutture", "Fondazioni + strutture"),
            ("opere_edili", "Opere edili"),
            ("impianti", "Impianti"),
            ("finiture", "Finiture"),
            ("serramenti", "Serramenti"),
            ("ascensore", "Ascensori"),
            ("predisposizioni_lift", "Predisposizioni home-lift"),
            ("fotovoltaico", "Fotovoltaico"),
            ("sistemazioni_esterne", "Sistemazioni esterne / viabilità"),
            ("marciapiede", "Marciapiedi"),
            ("allacci", "Allacci"),
        ]
        cols = st.columns(3)
        for idx, (k, label) in enumerate(fields):
            with cols[idx % 3]:
                c[k] = st.number_input(
                    f"{label} (€)", 0.0,
                    value=float(c.get(k, 0)),
                    step=5000.0,
                    key=f"cost_{k}"
                )

    st.markdown("#### Incidenze aggiuntive")
    c1, c2, c3, c4 = st.columns(4)
    c["spese_tecniche_pct"] = c1.number_input("Spese tecniche (%)", 0.0, value=float(c.get("spese_tecniche_pct", 0)), step=.5)
    c["imprevisti_pct"] = c2.number_input("Imprevisti (%)", 0.0, value=float(c.get("imprevisti_pct", 0)), step=.5)
    c["oneri"] = c3.number_input("Oneri / contributi (€)", 0.0, value=float(c.get("oneri", 0)), step=5000.0)
    c["finanziamento"] = c4.number_input("Finanziamento / interessi (€)", 0.0, value=float(c.get("finanziamento", 0)), step=5000.0)

    cr = calc_costs(p)
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Lavori", euro(cr["lavori"]))
    x2.metric("Spese tecniche", euro(cr["tecniche"]))
    x3.metric("Imprevisti", euro(cr["imprevisti"]))
    x4.metric("Costo sviluppo", euro(cr["sviluppo"]))

    with st.expander("Come è calcolato il costo sviluppo?", expanded=False):
        if float(c.get("costo_sviluppo_override", 0)) > 0:
            st.write(f'**Override attivo:** il costo sviluppo è assunto direttamente pari a {euro(c.get("costo_sviluppo_override",0))}.')
        elif c.get("modalita_costi") == "Parametrico €/m²":
            base = float(c.get("superficie_costo_mq",0)) * float(c.get("costo_parametrico_mq",0))
            st.write(f'**Lavori:** {fmt(c.get("superficie_costo_mq",0),0)} m² × {euro(c.get("costo_parametrico_mq",0))}/m² = {euro(base)}')
            if float(c.get("extra_parametrici",0)) > 0:
                st.write(f'+ Extra non compresi = {euro(c.get("extra_parametrici",0))}')
            st.write(f'**Spese tecniche:** {euro(cr["lavori"])} × {fmt(c.get("spese_tecniche_pct",0),2)}% = {euro(cr["tecniche"])}')
            st.write(f'**Imprevisti:** {euro(cr["lavori"])} × {fmt(c.get("imprevisti_pct",0),2)}% = {euro(cr["imprevisti"])}')
        else:
            st.write(f'**Lavori:** somma delle macro-voci dettagliate = {euro(cr["lavori"])}')
            st.write(f'**Spese tecniche:** {euro(cr["lavori"])} × {fmt(c.get("spese_tecniche_pct",0),2)}% = {euro(cr["tecniche"])}')
            st.write(f'**Imprevisti:** {euro(cr["lavori"])} × {fmt(c.get("imprevisti_pct",0),2)}% = {euro(cr["imprevisti"])}')
        if p.get("onorario_studio", {}).get("includi_nei_costi_sviluppo", False):
            st.write(f'**Spese tecniche collegate all’Onorario Studio:** {euro(cr["tecniche"])} (sostituiscono la percentuale generica).')
        st.write(f'**Costo sviluppo:** lavori + spese tecniche + imprevisti + oneri + finanziamento = **{euro(cr["sviluppo"])}**')

with tabs[5]:
    st.markdown("### Mercato")
    if p["analisi"].get("modalita_ricavi") == "Sintetico €/m²":
        m = p["mercato"]; st.caption("Metodo sintetico: €/m² residenziale + valore box.")
        for s, label in SCENARIOS:
            c1, c2, c3 = st.columns([1.2, 1, 1]); c1.markdown(f"**{label}**")
            m[f"prezzo_mq_{s}"] = c2.number_input(f"€/m² {label}", 0.0, value=float(m.get(f"prezzo_mq_{s}", 0)), step=50.0, key=f"pmq_{s}")
            m[f"box_{s}"] = c3.number_input(f"Box € {label}", 0.0, value=float(m.get(f"box_{s}", 0)), step=500.0, key=f"box_{s}")
    else:
        st.info("I prezzi di mercato sono impostati direttamente per ogni tipologia nel Product Mix. Qui trovi il riepilogo.")
        rows = []
        for row in p.get("mix_prodotti", []):
            rows.append({"Tipologia": row.get("tipologia"), "N.": row.get("n"), "Sup. media": f'{fmt(row.get("sup_media_mq",0),0)} m²', "Prudente": euro(row.get("prezzo_prudente",0)), "Probabile": euro(row.get("prezzo_probabile",0)), "Ottimistico": euro(row.get("prezzo_ottimistico",0))})
        st.dataframe(rows, hide_index=True, use_container_width=True)
    rr = calc_project(p)
    st.markdown("#### Valore complessivo")
    cols = st.columns(3)
    for col, (s, label) in zip(cols, SCENARIOS): col.metric(label, euro(rr["scenari"][s]["ricavi"]))

with tabs[6]:
    st.markdown("### Alternative progettuali")
    st.caption("Confronta concept diversi senza alterare il progetto attivo. Ogni alternativa usa un costo sviluppo sintetico e un proprio mix prodotti.")
    alts = p.setdefault("alternative", {})
    if not alts:
        st.info("Nessuna alternativa configurata per questo progetto.")
    for name, alt in alts.items():
        with st.expander(name, expanded=True):
            alt["costo_sviluppo"] = st.number_input("Costo sviluppo (€)", 0.0, value=float(alt.get("costo_sviluppo", 0)), step=10000.0, key=f"altcost_{slug(name)}")
            ar = calc_alternative(alt, float(p["acquisizione"].get("target_margin_pct", 18)))
            rows = []
            for s, label in SCENARIOS:
                x = ar[s]; rows.append({"Scenario": label, "Ricavi": euro(x["ricavi"]), "Costo": euro(x["costo"]), "Residuo pre-suolo": euro(x["residuo"]), "Max suolo/permuta al target": euro(x["max_land"])})
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption("Mix dell'alternativa")
            st.dataframe([{"Tipologia": x.get("tipologia"), "N.": x.get("n"), "Sup. media": x.get("sup_media_mq"), "Prezzo probabile": euro(x.get("prezzo_probabile",0))} for x in alt.get("mix_prodotti", [])], hide_index=True, use_container_width=True)

with tabs[7]:
    st.markdown("### Incentivi e premialità")
    i = p["incentivi"]; c1, c2 = st.columns(2)
    with c1:
        i["itaca_attivo"] = st.checkbox("ITACA attivo", value=bool(i.get("itaca_attivo", False)))
        i["itaca_pct"] = st.number_input("Bonus ITACA (%)", 0.0, value=float(i.get("itaca_pct", 0)), step=.5)
        it_opts = ["Verificato", "Da verificare oltre densità ordinaria", "Da verificare", "Non applicabile"]
        cur = i.get("itaca_stato", "Da verificare"); i["itaca_stato"] = st.selectbox("Stato ITACA", it_opts, index=it_opts.index(cur) if cur in it_opts else 2)
    with c2:
        i["romani_attivo"] = st.checkbox("Decreto Romani attivo", value=bool(i.get("romani_attivo", False)))
        i["romani_pct"] = st.number_input("Bonus Romani (%)", 0.0, value=float(i.get("romani_pct", 0)), step=.5)
        ro_opts = ["Verificato", "Da verificare cumulabilità/applicabilità", "Da verificare", "Non applicabile"]
        cur = i.get("romani_stato", "Da verificare"); i["romani_stato"] = st.selectbox("Stato Romani", ro_opts, index=ro_opts.index(cur) if cur in ro_opts else 2)
    i["nota"] = st.text_area("Nota incentivi", i.get("nota", ""))
    rr = calc_project(p); ur = rr["urbanistica"]
    a, b, c = st.columns(3); a.metric("Bonus teorico", f'{fmt(ur["bonus_pct"])}%'); b.metric("Volume incentivato teorico", f'{fmt(ur["vol_incentivato"],0)} m³'); c.metric("Scarto vs progetto", f'{fmt(ur["vol_incentivato"]-ur["vol_progetto"],0)} m³')
    st.warning("Le premialità restano scenari di verifica finché non è confermata la loro effettiva utilizzabilità sul caso specifico.")
    if p["meta"].get("tipologia_intervento") == "Demolizione + ricostruzione":
        st.markdown("#### Sismabonus · screening")
        i["sismabonus_attivo"] = st.checkbox(
            "Considera il Sismabonus nell'analisi fiscale",
            value=bool(i.get("sismabonus_attivo", False)),
            help="Attiva lo screening fiscale; il beneficio viene poi parametrizzato nella scheda Detrazioni 2026."
        )
        i["sismabonus_stato"] = st.selectbox(
            "Stato verifica Sismabonus",
            ["Da verificare requisiti fiscali e tecnici", "Potenzialmente applicabile", "Verificato", "Non applicabile"],
            index=(["Da verificare requisiti fiscali e tecnici", "Potenzialmente applicabile", "Verificato", "Non applicabile"].index(i.get("sismabonus_stato"))
                   if i.get("sismabonus_stato") in ["Da verificare requisiti fiscali e tecnici", "Potenzialmente applicabile", "Verificato", "Non applicabile"] else 0)
        )
        st.info("Per demolizione + ricostruzione l'app gestisce sia Sismabonus interventi sia Sismabonus acquisti. Sullo stesso intervento vanno verificati alternatività, zona sismica, asseverazioni e requisiti del soggetto.")

with tabs[8]:
    st.markdown("### Detrazioni fiscali 2026")
    f = p.setdefault("agevolazioni_fiscali", {})
    deep_defaults(f, default_tax_reliefs())
    st.caption(
        "Modulo preliminare attivabile voce per voce. Le aliquote 2026 sono preimpostate, "
        "ma restano modificabili per gestire casi particolari o futuri aggiornamenti."
    )

    g1, g2, g3 = st.columns(3)
    f["abitazione_principale"] = g1.checkbox(
        "Immobile adibito ad abitazione principale",
        value=bool(f.get("abitazione_principale", False))
    )
    f["titolare_proprieta_o_diritto_reale"] = g2.checkbox(
        "Beneficiario proprietario / titolare diritto reale",
        value=bool(f.get("titolare_proprieta_o_diritto_reale", False))
    )
    f["reddito_complessivo_euro"] = g3.number_input(
        "Reddito complessivo beneficiario (€)",
        min_value=0.0,
        value=float(f.get("reddito_complessivo_euro", 0)),
        step=5000.0
    )
    f["figli_fiscalmente_a_carico"] = st.number_input(
        "Figli fiscalmente a carico · dato utile per verifica limite detrazioni",
        min_value=0,
        value=int(f.get("figli_fiscalmente_a_carico", 0)),
        step=1
    )
    f["applica_limite_detrazioni_over_75000"] = st.checkbox(
        "Segnala limite complessivo detrazioni per redditi oltre €75.000",
        value=bool(f.get("applica_limite_detrazioni_over_75000", True))
    )

    labels = [
        ("bonus_casa", "Bonus ristrutturazioni / recupero edilizio"),
        ("ecobonus", "Ecobonus"),
        ("sismabonus_interventi", "Sismabonus interventi"),
        ("sismabonus_acquisti", "Sismabonus acquisti · demolizione e ricostruzione"),
        ("bonus_mobili", "Bonus mobili"),
        ("barriere_bonus_casa", "Eliminazione barriere · Bonus casa"),
        ("acquisto_immobile_ristrutturato", "Acquisto immobile interamente ristrutturato"),
    ]

    dets = f.setdefault("detrazioni", {})
    for key, title in labels:
        d = dets[key]
        # Sismabonus acquisti resta visibile sempre, ma evidenziamo la coerenza con il tipo intervento.
        if key == "sismabonus_acquisti" and p["meta"].get("tipologia_intervento") != "Demolizione + ricostruzione":
            exp_label = f"{title} · non coerente con il tipo intervento attuale"
        else:
            exp_label = title
        with st.expander(exp_label, expanded=bool(d.get("attivo", False))):
            d["attivo"] = st.checkbox("Attiva agevolazione", value=bool(d.get("attivo", False)), key=f"tax_on_{key}")

            c1, c2, c3 = st.columns(3)
            d["spesa_prevista_euro"] = c1.number_input(
                "Spesa / prezzo di riferimento (€)",
                min_value=0.0,
                value=float(d.get("spesa_prevista_euro", 0)),
                step=5000.0,
                key=f"tax_spesa_{key}"
            )
            d["unita_agevolabili"] = c2.number_input(
                "Unità agevolabili",
                min_value=1,
                value=max(int(d.get("unita_agevolabili", 1)), 1),
                step=1,
                key=f"tax_unit_{key}"
            )
            d["massimale_spesa_per_unita_euro"] = c3.number_input(
                "Massimale per unità (€) · 0 = manuale/non applicato",
                min_value=0.0,
                value=float(d.get("massimale_spesa_per_unita_euro", 0)),
                step=5000.0,
                key=f"tax_cap_{key}"
            )

            if key.startswith("sismabonus"):
                d["zona_sismica"] = st.selectbox(
                    "Zona sismica",
                    [0, 1, 2, 3, 4],
                    index=[0, 1, 2, 3, 4].index(int(d.get("zona_sismica", 0) or 0)) if int(d.get("zona_sismica", 0) or 0) in [0,1,2,3,4] else 0,
                    format_func=lambda x: "Da verificare" if x == 0 else f"Zona {x}",
                    key=f"tax_zone_{key}"
                )

            if key == "acquisto_immobile_ristrutturato":
                d["base_forfettaria_pct"] = st.number_input(
                    "Quota forfettaria del prezzo che costituisce base (%)",
                    min_value=0.0, max_value=100.0,
                    value=float(d.get("base_forfettaria_pct", 25)),
                    step=1.0,
                    key=f"tax_basepct_{key}"
                )

            d["usa_aliquota_manuale"] = st.checkbox(
                "Imposta aliquota manuale",
                value=bool(d.get("usa_aliquota_manuale", False)),
                key=f"tax_manual_{key}"
            )
            if d["usa_aliquota_manuale"]:
                d["aliquota_manuale_pct"] = st.number_input(
                    "Aliquota manuale (%)",
                    min_value=0.0, max_value=100.0,
                    value=float(d.get("aliquota_manuale_pct", 0)),
                    step=1.0,
                    key=f"tax_rate_{key}"
                )

            st.caption(d.get("nota", ""))

    tx = calc_tax_reliefs(p)
    st.markdown("#### Riepilogo detrazioni attive")
    if tx["rows"]:
        st.dataframe(
            [{
                "Agevolazione": x["nome"],
                "Spesa indicata": euro(x["spesa"]),
                "Base agevolata": euro(x["base"]),
                "Aliquota": f'{fmt(x["aliquota"])}%',
                "Detrazione teorica": euro(x["beneficio"]),
                "Ripartizione": f'{x["anni"]} anni',
                "Quota annua teorica": euro(x["quota_annua"]),
                "Beneficiario": x["beneficiario"],
            } for x in tx["rows"]],
            hide_index=True,
            use_container_width=True
        )
        k1, k2 = st.columns(2)
        k1.metric("Detrazioni teoriche complessive", euro(tx["totale_teorico"]))
        k2.caption("Le detrazioni lato acquirente/contribuente non vengono sottratte automaticamente ai costi né sommate ai ricavi dell'impresa.")
    else:
        st.info("Nessuna agevolazione fiscale attivata.")

    for w in tx["warnings"]:
        st.warning(w)
    f["note"] = st.text_area("Note fiscali / verifiche", f.get("note", ""))


with tabs[9]:
    st.markdown("### Acquisizione / Permuta")
    a = p["acquisizione"]; modes = ["Acquisto", "Permuta", "Mista"]
    a["modalita"] = st.selectbox("Modalità", modes, index=modes.index(a.get("modalita")) if a.get("modalita") in modes else 0)
    c1, c2, c3 = st.columns(3)
    a["prezzo_acquisto"] = c1.number_input("Prezzo acquisto (€)", 0.0, value=float(a.get("prezzo_acquisto", 0)), step=10000.0)
    a["permuta_pct"] = c2.slider("Permuta (% valore realizzato)", 0.0, 40.0, float(a.get("permuta_pct", 0)), .5)
    a["cash_mista"] = c3.number_input("Cash in modalità mista (€)", 0.0, value=float(a.get("cash_mista", 0)), step=10000.0)
    a["target_margin_pct"] = st.number_input("Margine obiettivo impresa (%)", 0.0, 50.0, float(a.get("target_margin_pct", 18)), .5)
    a["usa_permuta_manuale"] = st.checkbox("Usa valore permuta manuale", value=bool(a.get("usa_permuta_manuale", False)))
    if a["usa_permuta_manuale"]:
        a["permuta_valore_manuale"] = st.number_input("Valore permuta manuale (€)", 0.0, value=float(a.get("permuta_valore_manuale", 0)), step=10000.0)
    ps = a.setdefault("permuta_superficie", {})
    deep_defaults(ps, default_permuta_surface())
    if a["modalita"] in ["Permuta", "Mista"]:
        st.markdown("#### Superficie equivalente della permuta")
        e1, e2 = st.columns(2)
        ps["usa_superficie_manuale"] = e1.checkbox(
            "Usa superficie reale/manuale della permuta",
            value=bool(ps.get("usa_superficie_manuale", False))
        )
        ps["usa_prezzo_mq_manuale"] = e2.checkbox(
            "Usa €/m² manuale per l'equivalenza",
            value=bool(ps.get("usa_prezzo_mq_manuale", False))
        )
        if ps["usa_superficie_manuale"]:
            ps["superficie_manual_mq"] = st.number_input(
                "Superficie effettivamente ceduta in permuta (m²)",
                min_value=0.0,
                value=float(ps.get("superficie_manual_mq", 0)),
                step=5.0
            )
        if ps["usa_prezzo_mq_manuale"]:
            ps["prezzo_mq_manuale_euro"] = st.number_input(
                "Valore commerciale di riferimento per la permuta (€/m²)",
                min_value=0.0,
                value=float(ps.get("prezzo_mq_manuale_euro", 0)),
                step=50.0
            )
        ps["nota"] = st.text_input("Nota superficie permuta", ps.get("nota", ""))

    rr = calc_project(p); s = rr["scenari"]["probabile"]
    ps_calc = calc_permuta_surface(p, s["permuta"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Permuta applicata", euro(s["permuta"]))
    c2.metric("Superficie equivalente", f'{fmt(ps_calc["superficie_mq"],1)} m²' if a["modalita"] in ["Permuta", "Mista"] else "—")
    c3.metric("Max acquisizione sostenibile", euro(s["max_acq"]))
    c4.metric("Permuta max teorica", f'{fmt(s["max_perm_pct"])}%')
    if a["modalita"] in ["Permuta", "Mista"]:
        metodo = "superficie reale/manuale" if ps_calc["manuale"] else f'valore permuta ÷ {euro(ps_calc["prezzo_mq"])} /m²'
        st.caption(f"Equivalenza calcolata con: {metodo}. Non sostituisce l'identificazione delle unità effettivamente cedute.")
        with st.expander("Come è calcolata la permuta?", expanded=False):
            st.write(f'**Valore permuta applicato:** {euro(s["permuta"])}')
            if ps_calc["manuale"]:
                st.write(f'**Superficie equivalente:** inserita manualmente = {fmt(ps_calc["superficie_mq"],1)} m²')
            else:
                st.write(f'**Superficie equivalente:** {euro(s["permuta"])} ÷ {euro(ps_calc["prezzo_mq"])} /m² = **{fmt(ps_calc["superficie_mq"],1)} m²**')
            st.caption("L'equivalenza economica non identifica automaticamente quali appartamenti/box saranno effettivamente ceduti.")

    if p.get("permuta_opzioni"):
        st.markdown("#### Opzioni negoziali preimpostate")
        rows = []
        for op in p["permuta_opzioni"]:
            val = float(op.get("valore_totale", 0)); margin = (s["ricavi"] - rr["costi"]["sviluppo"] - val) / s["ricavi"] * 100 if s["ricavi"] else 0
            pmq = probable_price_per_mq(p); mqeq = val / pmq if pmq else 0.0
            rows.append({"Opzione": op.get("nome"), "Composizione": op.get("descrizione"), "Valore riconosciuto": euro(val), "Superficie equivalente": f'{fmt(mqeq,1)} m²', "Margine teorico": f'{fmt(margin)}%'})
        st.dataframe(rows, hide_index=True, use_container_width=True)

with tabs[10]:
    st.markdown("### Onorario Studio")
    st.caption("Modulo gestionale/commerciale per costruire il compenso per prestazioni. I preset sono sperimentali e completamente modificabili.")

    ensure_professional_fee(p)
    o = p["onorario_studio"]
    preset_names = [
        "Lavori interni completi",
        "Lavori interni parziali / restyling",
        "Ristrutturazione edilizia completa",
        "Demolizione e ricostruzione / nuova costruzione",
        "Solo direzione lavori",
        "Personalizzato",
    ]
    cur_preset = o.get("preset", preset_names[0])
    if cur_preset not in preset_names:
        cur_preset = preset_names[0]

    a1, a2 = st.columns([2,1])
    o["preset"] = a1.selectbox("Tipologia incarico / preset", preset_names, index=preset_names.index(cur_preset))
    if a2.button("Carica / ripristina preset", use_container_width=True):
        o["prestazioni"] = professional_fee_preset(o["preset"])
        st.rerun()

    if not o.get("prestazioni") and o["preset"] != "Personalizzato":
        o["prestazioni"] = professional_fee_preset(o["preset"])

    st.markdown("#### Basi di calcolo")
    b1, b2, b3 = st.columns(3)
    if float(o.get("superficie_mq", 0)) <= 0:
        o["superficie_mq"] = float(p.get("costi", {}).get("superficie_costo_mq", 0) or total_sale_area(p) or 0)
    o["superficie_mq"] = b1.number_input("Superficie incarico (m²)", 0.0, value=float(o.get("superficie_mq",0)), step=10.0)
    o["usa_base_lavori_manuale"] = b2.checkbox("Inserisci costo lavori manuale", value=bool(o.get("usa_base_lavori_manuale",False)))
    if o["usa_base_lavori_manuale"]:
        o["base_lavori_manual_euro"] = b3.number_input("Costo lavori di riferimento (€)", 0.0, value=float(o.get("base_lavori_manual_euro",0)), step=5000.0)
    else:
        b3.metric("Costo lavori collegato", euro(base_lavori_for_fee(p)))

    st.markdown("#### Prestazioni")
    st.caption("Attiva solo ciò che rientra nell'incarico. Per le voci €/m², quantità 0 = usa automaticamente la superficie incarico.")
    metodi = ["€/m²", "% lavori", "Forfait", "€/unità"]
    remove_idx = None
    for idx, row in enumerate(o.get("prestazioni", [])):
        with st.expander(f'{"✓" if row.get("attivo",False) else "○"} {row.get("nome","Prestazione")}', expanded=False):
            c1, c2 = st.columns([1,3])
            row["attivo"] = c1.checkbox("Attiva", value=bool(row.get("attivo",False)), key=f"fee_active_{idx}")
            row["nome"] = c2.text_input("Prestazione", value=row.get("nome",""), key=f"fee_name_{idx}")
            c3, c4, c5 = st.columns(3)
            metodo = row.get("metodo","Forfait")
            row["metodo"] = c3.selectbox("Metodo", metodi, index=metodi.index(metodo) if metodo in metodi else 2, key=f"fee_method_{idx}")
            row["quantita"] = c4.number_input("Quantità", 0.0, value=float(row.get("quantita",1)), step=1.0, key=f"fee_qty_{idx}")
            lab = "Tariffa (€/m²)" if row["metodo"] == "€/m²" else ("Aliquota (%)" if row["metodo"] == "% lavori" else "Tariffa (€)")
            row["tariffa"] = c5.number_input(lab, 0.0, value=float(row.get("tariffa",0)), step=0.5 if row["metodo"] == "% lavori" else 50.0, key=f"fee_rate_{idx}")
            if st.button("Elimina prestazione", key=f"fee_del_{idx}"):
                remove_idx = idx
    if remove_idx is not None:
        o["prestazioni"].pop(remove_idx)
        st.rerun()

    if st.button("＋ Aggiungi prestazione"):
        o.setdefault("prestazioni", []).append({"attivo": True, "nome": "Nuova prestazione", "metodo": "Forfait", "quantita": 1.0, "tariffa": 0.0})
        st.rerun()

    st.markdown("#### Proposta al cliente e margine studio")
    d1, d2, d3 = st.columns(3)
    o["sconto_pct"] = d1.number_input("Sconto commerciale (%)", 0.0, 100.0, value=float(o.get("sconto_pct",0)), step=1.0)
    o["costi_collaboratori_euro"] = d2.number_input("Collaboratori / consulenti (€)", 0.0, value=float(o.get("costi_collaboratori_euro",0)), step=500.0)
    o["altri_costi_diretti_euro"] = d3.number_input("Altri costi diretti commessa (€)", 0.0, value=float(o.get("altri_costi_diretti_euro",0)), step=500.0)

    e1, e2, e3, e4 = st.columns(4)
    o["contributo_integrativo_attivo"] = e1.checkbox("Contributo integrativo", value=bool(o.get("contributo_integrativo_attivo",True)))
    o["contributo_integrativo_pct"] = e2.number_input("Contributo (%)", 0.0, value=float(o.get("contributo_integrativo_pct",4)), step=0.5)
    o["iva_attiva"] = e3.checkbox("IVA", value=bool(o.get("iva_attiva",True)))
    o["iva_pct"] = e4.number_input("IVA (%)", 0.0, value=float(o.get("iva_pct",22)), step=1.0)

    fee = calc_professional_fee(p)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Onorario teorico", euro(fee["teorico"]))
    k2.metric("Onorario proposto", euro(fee["proposto"]))
    k3.metric("Compenso effettivo", f'{fmt(fee["euro_mq"],1)} €/m²')
    k4.metric("Incidenza sui lavori", f'{fmt(fee["incidenza_pct"],2)}%')

    m1, m2, m3 = st.columns(3)
    m1.metric("Totale fattura indicativo", euro(fee["totale_cliente"]))
    m2.metric("Margine lordo studio", euro(fee["margine_studio"]))
    m3.metric("Margine studio / onorario", f'{fmt(fee["margine_studio_pct"],1)}%')

    o["includi_nei_costi_sviluppo"] = st.checkbox(
        "Usa l'onorario proposto come 'Spese tecniche' nel costo di sviluppo",
        value=bool(o.get("includi_nei_costi_sviluppo",False)),
        help="Se attivo, sostituisce la percentuale generica 'Spese tecniche (%)' nella scheda Costi, evitando il doppio conteggio."
    )
    if o["includi_nei_costi_sviluppo"]:
        st.warning("Collegamento attivo: nel business plan le spese tecniche sono sostituite dall'onorario proposto dello studio.")

    with st.expander("Come è calcolato l'onorario?", expanded=False):
        st.write(f'**Superficie incarico:** {fmt(fee["superficie"],1)} m²')
        st.write(f'**Costo lavori di riferimento:** {euro(fee["base_lavori"])}')
        for row in fee["rows"]:
            st.write(f'**{row["nome"]}:** {row["formula"]} = {euro(row["valore"])}')
        st.write(f'**Onorario teorico:** {euro(fee["teorico"])}')
        st.write(f'**Sconto:** {fmt(o.get("sconto_pct",0),1)}% = − {euro(fee["sconto"])}')
        st.write(f'**Onorario proposto:** {euro(fee["proposto"])}')
        st.write(f'**Margine lordo studio:** {euro(fee["proposto"])} − {euro(fee["collaboratori"])} − {euro(fee["altri_costi"])} = **{euro(fee["margine_studio"])}**')
        if o.get("contributo_integrativo_attivo",True):
            st.write(f'Contributo integrativo: {euro(fee["contributo"])}')
        if o.get("iva_attiva",True):
            st.write(f'IVA: {euro(fee["iva"])}')
        st.write(f'**Totale fattura indicativo:** {euro(fee["totale_cliente"])}')

    st.info("I preset servono a costruire il tuo tariffario interno. Dopo alcuni incarichi potremo sostituire i valori iniziali con le medie reali Oltreforma.")


with tabs[11]:
    st.markdown("### Report e dati")
    rr = calc_project(p)
    st.download_button("Genera report PDF", data=make_pdf(p, rr), file_name=f'{slug(p["meta"]["name"])}_fattibilita.pdf', mime="application/pdf", use_container_width=True)
    raw = json.dumps(p, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button("Esporta progetto JSON", data=raw, file_name=f'{slug(p["meta"]["name"])}.json', mime="application/json", use_container_width=True)
    all_raw = json.dumps(st.session_state.projects, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button("Backup archivio progetti", data=all_raw, file_name="projects_backup.json", mime="application/json", use_container_width=True)
    st.caption("Nota: su Streamlit Community Cloud la scrittura locale può non essere persistente dopo riavvii/redeploy. Il file data/projects.json nel repository resta la base durevole.")

with tabs[12]:
    st.markdown("### Guida / Legenda")
    st.caption("Legenda pratica dei principali dati e delle formule usate dall'app. Serve a leggere i risultati, non sostituisce le verifiche urbanistiche, fiscali, estimative o strutturali.")

    st.markdown("#### Urbanistica")
    st.markdown("""
- **St** = superficie territoriale. Con **Ift** genera il volume territoriale: `St × Ift`.
- **Sf** = superficie fondiaria. Con **Iff** genera il volume fondiario: `Sf × Iff`.
- **Volume esistente legittimo** = volume documentato/verificato dell'edificio esistente; può essere inserito direttamente o ricostruito per livelli.
- **Piano Casa / premialità** = scenario teorico calcolato sul volume esistente. Deve essere attivato solo dopo verifica dell'applicabilità al caso concreto.
- **Volume da titolo/progetto approvato** = volume già assentito/documentato.
- **Volume disponibile assunto** = la fonte volumetrica che scegli di usare nel business plan.
- **Volume di progetto** = volume dell'ipotesi progettuale.
- **Residuo / eccedenza** = `volume disponibile − volume di progetto`. Positivo = residuo; negativo = eccedenza.
""")

    st.markdown("#### Costi")
    st.markdown("""
- **Parametrico €/m²** = `superficie di riferimento × costo €/m² + extra`.
- **Dettagliato** = somma delle macro-voci di costo.
- **Spese tecniche** e **imprevisti** sono percentuali applicate ai lavori.
- **Costo sviluppo** = lavori + spese tecniche + imprevisti + oneri + finanziamento.
- **Override**: se maggiore di zero sostituisce l'intero calcolo del costo sviluppo.
""")

    st.markdown("#### Mercato, margine e acquisizione")
    st.markdown("""
- **Valore commerciale / ricavi** = superficie × prezzo di vendita oppure somma del Product Mix.
- **Utile** = ricavi − costo sviluppo − costo di acquisizione/permuta.
- **Margine** = `utile ÷ ricavi × 100`.
- **Max acquisizione al target** = importo massimo riconoscibile al proprietario mantenendo il margine obiettivo impostato.
""")

    st.markdown("#### Permuta")
    st.markdown("""
- **Valore permuta** = valore economico riconosciuto al proprietario in immobili.
- **Superficie equivalente** = `valore permuta ÷ valore commerciale €/m²`, salvo inserimento manuale della superficie reale ceduta.
- La superficie equivalente è un indicatore economico: non sostituisce la scelta delle unità effettive da cedere.
""")

    st.markdown("#### Detrazioni")
    st.markdown("""
- Le detrazioni sono mostrate come **beneficio teorico del contribuente/acquirente** e non vengono sommate automaticamente ai ricavi dell'impresa.
- Massimali, aliquote, beneficiari, requisiti e cumulabilità devono essere verificati sul caso concreto.
""")

    st.markdown("#### Onorario Studio")
    st.markdown("""
- **Onorario teorico** = somma delle sole prestazioni attive.
- Le prestazioni possono essere calcolate a **€/m²**, **% lavori**, **forfait** oppure **€/unità**.
- **Onorario proposto** = onorario teorico − eventuale sconto commerciale.
- **Compenso effettivo €/m²** = onorario proposto ÷ superficie incarico.
- **Incidenza sui lavori** = onorario proposto ÷ costo lavori × 100.
- **Margine lordo studio** = onorario proposto − collaboratori/consulenti − altri costi diretti della commessa.
- Se attivi il collegamento ai costi, l'onorario proposto sostituisce la percentuale generica delle **spese tecniche**, evitando il doppio conteggio.
- Contributo integrativo e IVA sono parametri modificabili e servono soltanto a stimare il totale fattura.
""")

    st.info("Suggerimento: nelle sezioni principali apri sempre **“Come è calcolato?”** per vedere la formula con i numeri del progetto corrente.")

# ---------- persist ----------
st.session_state.projects[st.session_state.current_project] = p
save_projects(st.session_state.projects)
