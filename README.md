# Oltreforma | Feasibility — V3.1

Web app Streamlit per valutazioni preliminari di fattibilità immobiliare.

## Novità V2
- Urbanistica con St/Sf, Ift/Iff e regime Fondiario/Convenzionato.
- Volume approvato/riferimento e volume progetto diretto o geometrico.
- Product Mix multi-tipologia con tre scenari di prezzo.
- Confronto alternative progettuali.
- Costi estesi, predisposizioni home-lift, sistemazioni esterne e finanziamento.
- Acquisizione/permuta con valore manuale e opzioni negoziali.
- Preset Via Matteotti preservato e Area B3 - Via Toscani aggiunta.
- Backup JSON dell'archivio progetti e report PDF V2.

> Nota: su Streamlit Community Cloud la scrittura locale può non essere persistente dopo restart/redeploy. Il file `data/projects.json` nel repository è la base durevole dei preset.


## Novità V3
- Sismabonus 2026, incluso **Sismabonus acquisti** per demolizione + ricostruzione, attivabile/disattivabile.
- Modulo **Detrazioni fiscali 2026** con Bonus casa, Ecobonus, Sismabonus, Bonus mobili, barriere architettoniche nell'ambito Bonus casa e acquisto di unità in edificio interamente ristrutturato.
- Aliquote e massimali sono parametrizzati e modificabili; il modello distingue il beneficio fiscale dell'acquirente/contribuente dai ricavi dell'impresa.
- In caso di permuta sono mostrati **valore, percentuale e superficie equivalente in m²**, con possibilità di inserire la superficie reale ceduta.
- Avvisi per potenziale sovrapposizione dei massimali e per il limite complessivo alle detrazioni con redditi superiori a €75.000.
- Report PDF aggiornato con superficie equivalente della permuta e totale teorico delle detrazioni attive.

### Nota fiscale
Il modulo è uno strumento preliminare di fattibilità e non sostituisce la verifica del commercialista/notaio né gli adempimenti tecnici e fiscali richiesti per la singola agevolazione.


## Novità V3.1 — Costi parametrici
- Modalità **Parametrico €/m²** impostata per screening rapido.
- Preset modificabili:
  - Manutenzione straordinaria leggera: 600 €/m²
  - Ristrutturazione media: 950 €/m²
  - Ristrutturazione pesante: 1.300 €/m²
  - Demolizione + ricostruzione: 1.800 €/m²
  - Nuova costruzione residenziale: 1.900 €/m²
  - Nuova costruzione medio-alta: 2.200 €/m²
- Possibilità di inserire superficie di riferimento, €/m² personalizzato ed extra non inclusi.
- Restano separati spese tecniche, imprevisti, oneri e finanziamento.
- La modalità **Dettagliato** resta disponibile per analisi più avanzate.
