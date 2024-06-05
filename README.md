# Praktični zadatak
|||
|-:|:-:|
|Kolegij|**Uvod u teorijsko računarstvo**|
|Nositelj predmeta|Prof. dr. sc. Sanda Martinčić-Ipšić|
|Asistent|Andrija Poleksić, mag. inf.|

## Izvor podataka

Kao izvor podataka je korišten skup časopisa [`Climate Dynamics (2021)`](https://link.springer.com/journal/382) © Springer-Verlag GmbH Germany.

## Korišteni alati/biblioteke

- beautiful soup (`beautifulsoup4`)
- pdfminer (`pdfminer.six`)
- camelot (`camelot`)
- pandas (`pandas`)
- openpyxl (`openpyxl`)
  - podržka za `xlsx` format
- python std lib

### Utilities

- PyPDF2
  - za popravak "potrganih" PDFova
  - CI javlja grešku da su "/Root" dokumenta ne postoji (ne lokalno)
- psutil (`psutil`)
  - broj fizičkih jezgri procesora

### Radno okruženje

- pipenv (pip + virtualenv)
- VSCode (`code` + `code-marketplace` + `code-features-insiders`)
  - Python (Microsoft)
  - Cody

## Struktura spremljenih podataka

Podaci su spremljeni u `json`, `csv`, `xlsx` i `pkl` formatima.

## Korišteni materijali

## Licenca/License

Kod u repozitoriju je licenciran terenarnom Apache 2.0/zlib/MIT, koristite
željenu. PDF datoteke u `data/` direktoriju sadrže sukladne podatke o vlasništvu
i koriste se kao popratni materijal (za obradu), javno su dostupne (otvoreni
pristup).

Code in this repository is licensed under Apache 2.0/zlib/MIT terenary license,
adhere to whichever you prefer. PDF files in `data/` directory contain
respective copyright information and are used as a reference material (for
processing examples), they are publicly available (open access).

If you want PDFs in `data/` directory to be removed, feel free to contact me and
I'll aim to remove them as soon as practicable.
