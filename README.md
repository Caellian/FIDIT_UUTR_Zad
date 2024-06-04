# Praktični zadatak

Kolegij: **Uvod u teorijsko računarstvo**

Nositelj predmeta: Prof. dr. sc. Sanda Martinčić-Ipšić

Asistent: Andrija Poleksić, mag. inf.

Autor koda: Tin Švagelj

Licenca: Apache 2.0/zlib/MIT

## Izvor podataka

Kao izvor podataka je korišten skup časopisa [`Climate Dynamics (2021)`](https://link.springer.com/journal/382) © Springer-Verlag GmbH Germany.

## Korišteni alati/biblioteke

- beautiful soup (`beautifulsoup4`)
- pdfminer (`pdfminer.six`)
- camelot (`camelot`)
- pandas (`pandas`)
- python std lib

### Radno okruženje

- pipenv (pip + virtualenv)
- VSCode (`code` + `code-marketplace` + `code-features-insiders`)
  - Python (Microsoft)
  - Cody

## Struktura spremljenih podataka

Podaci su spremljeni u `json`, `csv`, `xlsx` i `pkl` formatima.

## Bilješke o izlučivanju podataka

npr. _U nekim radovima nije bilo moguće izlučiti podnaslove jer se ne razlikuju od ostatka teksta._

# Upute

5. Predati:
   - **Kod s pripadnom dokumentacijom, preporuka je Python notebook** (.ipynb)
   - **Dokumentacija** (5.)
   - **Rezultati izlučivanja** - .csv, .json, ... datoteke

---

> Komentari:
>
> > Ideja je tekst očuvati što konzistentnijim.
> >
> > Česti problemi sa ekstrakcijom:

| Problem Description                                            | Example/Explanation                                                                                                                                                                              |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Text data missing due to unexpected font size/style            | Where $2$ and $two$ always makes up five.<br />**Where and always makes up five.** <br /> ... original BERT<sub>BASE</sub> model with ... <br /> **... original BERT model with ...**            |
| Wrong ordering of paragraphs                                   | Layout algorithm heuristics give wrong conclusions based on distance, e.g. bottom right paragraph is "closer" to top right paragraph then to the top left paragraph due to a figure/table/graph. |
| Page numbering or similar information abrupt paragraph content | For navigation through HTML files, we used BeautifulSoup library. <br /> **For navigation through HTML files, we PAGE 5 AUTHOR ET AL. used BeautifulSoup library.**                              |
| Wrong word ordering due to justification                       | Nature &nbsp; &nbsp; &nbsp; climate <br /> change <br /> **Nature change climate**                                                                                                               |
| Problems with wrong symbol extraction (Ligatures)              | ... far-reaching effects on global ecosystems ... <br /> **... far-reaching eﬀects on global ecosystems ...**                                                                                    |
| First line of paragraph missing                                |                                                                                                                                                                                                  |

> > Primjer bilješki o izlučivanju:

````markdown
1. Impact of a large artificial lake on regional climate: A typical meteorological year Meso-NH simulation results (2021.)
   - Missing text:
   ```txt
   2.3.1 Typical Meteorological Year
   A TMY consists of 12 concatenated months representing the typical climatological
   conditions for a particular area.
   .
   .
   .
   More information on the generation of TMY can be found in the work of Abreu et
   al. (2018).
   ```
   - Correct ordering of text, correct authors
   - +-++
2. Changes in surface shortwave solar irradiance from 1993 to 2011 at Thessaloniki (Greece) (2012.)
   - Text alright
   - Double appearence of authors (irrelevant)
   - ++-+
3. Comments on the review article by E. C. Barrett on the NASA workshop ‘precipitation measurements from space’ (1983.)
   - ++++
4. Uncertainty in regional climate model outputs over the Czech Republic: the role of nested and driving models (2014.)
   - Missing text:
   ```txt
   To assess the uncertainties in both MMEs, the analysis of variance described by
   D´equ´e et al. (2007) was employed.
   .
   .
   .
   In each of the next iterations we calculate missing X ij using following equation:
   ```
   - Double appearence of authors (irrelevant)
   - +--+
5. Biases in sea surface temperature and the annual cycle of Greater Horn of Africa rainfall in CMIP6 (2021.)
   - Double authors
   - NOTE: no content in source file (check why?)
   - +--+
6. Cut-off low systems over Iraq: Contribution to annual precipitation and synoptic analysis of extreme events (2019.)
   - Missing text:
   ```txt
   The moisture flux is vertically-integrated between 1000 and 700 hP ...
   .
   .
   .
   Note that in these definitions VIMF is a vector while VIMFC is a scalar.
   ```
   - After Acknowledgement, there is tabel and figure descriptions (irrelavant)
   - Double authors
   - +--+
7. Projected changes of typhoon intensity in a regional climate model: Development of a machine learning bias correction scheme (2020.)
   - Double authors
   - ++-+
8. Internal atmospheric variability of net surface heat flux in reanalyses and CMIP5 AMIP simulations (2021.)
   - Missing text:
   ```txt
   The 1979–2008 monthly mean NHF in four atmospheric reanalyses and a set of CM ...
   .
   .
   .
   reanalysis and model, the decomposition is written as ...
   ```
   - Double authors
   - +--+
9. Evaluation of a new satellite-based precipitation data set for climate studies in the Xiang River basin, southern China (2017.)
   - No content
   - Abstract present
   - Double authors
   - +--+
10. Interdecadal changes of summer precipitation dominant mode over East Asia-Northwest Pacific around late 1990s (2021.)
    - No content
    - Abstract present
    - Double authors
    - +--+

## Conclusion

- Not all samples have full text, most of missing text is from around equations or unavailable papers
- All samples have double instances for each author (not a problem)
- Samples were within the climate change topic and up to date (2012. - 2022.)
- **PROBLEM 1:** Missing text should be explored further -> Check why are the equations a problem and check why some text have only abstract
````
