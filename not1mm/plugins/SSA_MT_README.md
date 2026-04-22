# SSA Månadstest (SSA MT) - Plugin för Not1MM

Plugin för SSA Månadstest CW och SSB, en svensk contest
arrangerat av Sveriges Sändareamatörer.

Regler: https://hfcontest.ssa.se/ssa-mt/regler.html
Logguppladdning: https://hfcontest.ssa.se/ssa-mt/

## Tävlingsinfo

- Hålls varje månad, söndagen närmast den 15:e
- Pass 1: 1400-1500 UTC, Pass 2: 1515-1615 UTC
- CW: 3525-3575 kHz, 7010-7040 kHz
- SSB: 3650-3750 kHz, 7060-7130 kHz
- Anrop: "CQ MT"
- Exchange: RS(T) + löpnummer (från 01) + 6-teckens lokator
- Exempel: 599 01 JP75XX
- Poäng: 2 per godkänt QSO
- Multiplar: unika 4-teckens lokatorrutor per band
- Slutpoäng: QSO-poäng x multiplar

## Installation

Pluginen består av två filer:
- not1mm/plugins/ssa_mt_cw.py
- not1mm/plugins/ssa_mt_ssb.py

Båda syns i Not1MM under File > New Contest efter installation.

## Manuell konfiguration vid första användning

### 1. Sent Exchange

Öppna File > Edit Current Contest och fyll i din 6-teckens
lokator i fältet "Sent Exchange", t.ex. JO67LC.
Detta värde används av {EXCH}-makrot när du sänder exchange.

### 2. CW-makrofil (SSA MT CW)

Filen skapas automatiskt första gången du väljer SSA MT CW,
men den generiska mallen stämmer inte för SSA MT.
Öppna File > Edit Macros och ersätt innehållet med följande:

S|F1|CQ|cq mt {MYCALL}
S|F2|HisCall|{HISCALL}
S|F3|Exch|{SNT} # {EXCH}
S|F4|empty|
S|F5|MyCall|{MYCALL}
S|F6|?|?
S|F7|Roger|rr
S|F8|QSO B4|qso b4
S|F9|AGN|agn
S|F10|Call?|cl?
S|F11|NR??|NR?
S|F12|LOC?|LOC?
R|F1|Run CQ|cq mt {MYCALL}
R|F2|HisCall|{HISCALL}
R|F3|Run Exch|{SNT} # {EXCH}
R|F4|Run TU|tu {MYCALL}
R|F5|MyCall|{MYCALL}
R|F6|MyNR|{SENTNR}
R|F7|?|?
R|F8|QSO B4|{HISCALL} qso b4
R|F9|AGN|agn
R|F10|Call?|cl?
R|F11|NR?|NR?
R|F12|LOC?|LOC?

Notera att # i makrot skickar löpnumret med förkortade siffror
enligt WinKeyer-inställningarna (T=0, N=9).

### 3. ESM-inställningar (Enter Sends Message)

Öppna File > Configuration Settings > Options och ställ in:
- Enable ESM: aktiverat
- CQ: F1
- His Call: F2
- Exchange: F3
- AGN: F9
- My Call: F5
- QRZ: F4
- QSO B4: F8  <---- OBS!

### 4. Cabrillo-logg

Loggen sparas i hemkatalogen med filnamnet:
ANROPSSIGNAL_SSA-MT-CW_DATUM_TID.log

Ladda upp via: https://hfcontest.ssa.se/ssa-mt/
Deadline: 2359 UTC, 7 dagar efter tävlingen.

## Arbetsflöde S&P (Search & Pounce)

1. Fyll i motstationens callsign
2. Tryck Enter - sänder ditt call ({MYCALL})
3. Fyll i mottaget Nr och Locator
4. Tryck Enter på Locator-fältet - sänder din exchange (599 # JO67LC)
5. Tryck Enter igen - loggar QSO:et

Om motparten säger AGN? efter steg 4, tryck F3 för att sända
exchange en gång till. När allt är klart trycker du Enter i
Locator-fältet ännu en gång för att logga.

## Arbetsflöde Run

1. F1 sänder CQ MT {MYCALL}
2. Fyll i motstationens callsign
3. Tryck Enter - sänder {HISCALL} följt av din exchange
4. Cursorn hoppar till Nr-fältet
5. Fyll i mottaget Nr, tryck Enter - hoppar till Locator
6. Fyll i mottagen Locator, tryck Enter - sänder TU {MYCALL} och loggar

Om ett fält är tomt när du trycker Enter:
- Tomt Nr-fält: sänder NR? (F11)
- Tom Locator: sänder LOC? (F12)

## Kända begränsningar

- Mottagen lokator valideras mot kända svenska lokatorrutor.
- Sänt löpnummer visas inte i UI under pågående QSO,
  men syns i loggfönstret efter att QSO loggats.
- CW-makromallen är generisk och måste ändras manuellt
  enligt instruktionerna ovan.

## Ändringslogg

2026-04-22 - Initial version skapad (feature/ssa-mt branch)
