# Oltreforma | Feasibility — V1

Web app Streamlit per valutazioni preliminari immobiliari.

## Funzioni V1
- Archivio locale progetti
- Nuovo progetto / duplicazione
- Vista Studio
- Vista Cliente / Impresa
- Urbanistica: lotto, Iff, volume ordinario, volume progetto, esclusione scala/ascensore
- Programma edilizio
- Costi di sviluppo
- Tre scenari di mercato: Prudente / Probabile / Ottimistico
- Incentivi ITACA / Decreto Romani con stato di verifica
- Acquisto / Permuta / Mista
- Permuta di riferimento e massimo teorico sostenibile
- Redditività e prezzo massimo sostenibile di acquisizione
- Report PDF
- Esportazione progetto JSON
- Caso Via Matteotti precaricato

## Avvio in locale
1. Installa Python 3.11 o superiore
2. Apri il terminale nella cartella
3. Esegui:
   pip install -r requirements.txt
   streamlit run app.py

## Pubblicazione
La cartella è pronta per essere messa su GitHub e pubblicata con Streamlit Community Cloud.
Per uso professionale multi-dispositivo si consiglia una V2 con database cloud e autenticazione.

## Nota
Le premialità volumetriche sono gestite come scenari di verifica. L'app non sostituisce la verifica urbanistica, normativa, fiscale, strutturale o estimativa professionale.
