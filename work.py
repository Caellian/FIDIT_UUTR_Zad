#!/usr/bin/env python3

import camelot
import pandas as pd

import PyPDF2
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams  # Podešavanje parametara
from bs4 import BeautifulSoup
import psutil

# python std lib
import os
from pathlib import Path
from io import StringIO
import glob
import re
import pickle
import json
from datetime import datetime
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import traceback
from types import SimpleNamespace

# sys.setrecursionlimit(8000)

DEBUG = True

# Dozvoljava podešavanje parametara kroz environment variables
OUT_DIR = os.environ.get("OUT_DIR", "./out")
IN_DIR = os.environ.get("IN_DIR", "./data")

WORKER_COUNT = os.environ.get("WORKER_COUNT", psutil.cpu_count(logical=False))
# Možemo koristiti i argparse pa postaviti os.environ vrijednosti, no nije bitno
# za ovaj zadatak


class InsufficientParser(Exception):
    pass


def map_style_val(name, value):
    """Ovisno o imenu CSS atributa mapira/čisti njegovu vrijednost"""
    if name in ["font-size", "top", "left", "width", "height"]:
        if value.endswith("px"):
            return value[:-2]
        else:
            raise Exception(f"Unknown font-size unit: {value}")
    return value


def style_kv_obj(style):
    """Mapira CSS style u Python objekte"""
    if not style or len(style) == 0:
        return None
    if style is object:
        # već obrađeno
        return style
    style = filter(
        lambda x: not len(x) == 0, map(lambda x: x.strip(), style.split(";"))
    )
    return {
        k.strip(): map_style_val(k.strip(), v.strip())
        for k, v in map(lambda x: x.split(":"), style)
    }


# Preprocessanje da daljnji style string searchevi imaju bolje performanse
# inlinea style atribute na HTML tagove
# Također dodaje atribut sa stranicom na svaki tag da olakša filtriranje kasnije.
def preprocess_soup(soup):
    """Obrađuje BS4 objekte kako bi bili pogodniji za obradu"""
    page_index = "0"
    for tag in soup.recursiveChildGenerator():
        if not hasattr(tag, "attrs"):
            continue
        style = tag.attrs.get("style")
        if style:
            style = style_kv_obj(style)
            if style is not None:
                for k, v in style.items():
                    tag.attrs[k] = v
            tag.attrs.pop("style")
        if tag.name == "a":
            name = tag.attrs.get("name")
            is_page = tag.text.strip().startswith("Page")
            if is_page and name is not None:
                page_index = name
        if tag.name != "br":
            tag.attrs["page"] = page_index

    return soup


def repaired_pdf(path):
    """
    Pokušava popraviti dani PDF dokument i vraća putanju na popravljeni file.
    """
    # https://github.com/pdfminer/pdfminer.six/issues/476
    repaired_filename = f"{path.replace('.pdf', '_repaired.pdf')}"

    with open(path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        # Create a new PDF
        with open(repaired_filename, "wb") as new_file:
            writer = PyPDF2.PdfWriter()

            # Copy content from old to new
            for i in range(len(reader.pages)):
                writer.add_page(reader.pages[i])

            writer.write(new_file)
    return repaired_filename


def pdf_soup(path):
    """
    Učitava PDF dokument u BS4 objekte, provodeći preprocessanje ako je
    potrebno.

    Također popravlja PDF ako se nije uspješno otvorio.
    """
    # Pretvorba iz PDFa u HTML pa u BS4 je dosta skupa, tako da pohranjujem
    # rezultate obrade za bržu iteraciju

    if not Path(path + ".html").is_file():
        print(f"Parsing {path} ... (not cached)")
        output_string = StringIO()
        try:
            fin = open(path, "rb")
            extract_text_to_fp(
                fin,
                output_string,
                laparams=LAParams(),
                output_type="html",
                codec=None,
            )
        except PDFSyntaxError as err:
            print(f"Error parsing '{path}': ", err)
            print(f"Trying to repair '{path}' PDF...")

            fin = open(repaired_pdf(path), "rb")
            extract_text_to_fp(
                fin,
                output_string,
                laparams=LAParams(),
                output_type="html",
                codec=None,
            )
            return None
        finally:
            fin.close()

        soup = BeautifulSoup(output_string.getvalue(), "html.parser")
        print(f"Preprocessing {path} ...")
        soup = preprocess_soup(soup)
        with open(path + ".html", "w") as fout:
            fout.write(soup.prettify())
        print("Done")
        return soup

    else:
        print(f"Loading cached {path}.html ...")
        with open(path + ".html", "r") as fin:
            soup = BeautifulSoup(fin.read(), "html.parser")
            print("Done")
            return soup

#################
# UTIL FUNKCIJE #
#################

# https://util.unicode.org/UnicodeJsps/list-unicodeset.jsp?a=[%3Aupper%3A]&abb=on&ucd=on&esc=on
_RE_UPPERCASE = r"[A-Z\u00C0-\u00D6\u00D8-\u00DE\u0100\u0102\u0104\u0106\u0108\u010A\u010C\u010E\u0110\u0112\u0114\u0116\u0118\u011A\u011C\u011E\u0120\u0122\u0124\u0126\u0128\u012A\u012C\u012E\u0130\u0132\u0134\u0136\u0139\u013B\u013D\u013F\u0141\u0143\u0145\u0147\u014A\u014C\u014E\u0150\u0152\u0154\u0156\u0158\u015A\u015C\u015E\u0160\u0162\u0164\u0166\u0168\u016A\u016C\u016E\u0170\u0172\u0174\u0176\u0178\u0179\u017B\u017D\u0181\u0182\u0184\u0186\u0187\u0189-\u018B\u018E-\u0191\u0193\u0194\u0196-\u0198\u019C\u019D\u019F\u01A0\u01A2\u01A4\u01A6\u01A7\u01A9\u01AC\u01AE\u01AF\u01B1-\u01B3\u01B5\u01B7\u01B8\u01BC\u01C4\u01C7\u01CA\u01CD\u01CF\u01D1\u01D3\u01D5\u01D7\u01D9\u01DB\u01DE\u01E0\u01E2\u01E4\u01E6\u01E8\u01EA\u01EC\u01EE\u01F1\u01F4\u01F6-\u01F8\u01FA\u01FC\u01FE\u0200\u0202\u0204\u0206\u0208\u020A\u020C\u020E\u0210\u0212\u0214\u0216\u0218\u021A\u021C\u021E\u0220\u0222\u0224\u0226\u0228\u022A\u022C\u022E\u0230\u0232\u023A\u023B\u023D\u023E\u0241\u0243-\u0246\u0248\u024A\u024C\u024E\u0370\u0372\u0376\u037F\u0386\u0388-\u038A\u038C\u038E\u038F\u0391-\u03A1\u03A3-\u03AB\u03CF\u03D2-\u03D4\u03D8\u03DA\u03DC\u03DE\u03E0\u03E2\u03E4\u03E6\u03E8\u03EA\u03EC\u03EE\u03F4\u03F7\u03F9\u03FA\u03FD-\u042F\u0460\u0462\u0464\u0466\u0468\u046A\u046C\u046E\u0470\u0472\u0474\u0476\u0478\u047A\u047C\u047E\u0480\u048A\u048C\u048E\u0490\u0492\u0494\u0496\u0498\u049A\u049C\u049E\u04A0\u04A2\u04A4\u04A6\u04A8\u04AA\u04AC\u04AE\u04B0\u04B2\u04B4\u04B6\u04B8\u04BA\u04BC\u04BE\u04C0\u04C1\u04C3\u04C5\u04C7\u04C9\u04CB\u04CD\u04D0\u04D2\u04D4\u04D6\u04D8\u04DA\u04DC\u04DE\u04E0\u04E2\u04E4\u04E6\u04E8\u04EA\u04EC\u04EE\u04F0\u04F2\u04F4\u04F6\u04F8\u04FA\u04FC\u04FE\u0500\u0502\u0504\u0506\u0508\u050A\u050C\u050E\u0510\u0512\u0514\u0516\u0518\u051A\u051C\u051E\u0520\u0522\u0524\u0526\u0528\u052A\u052C\u052E\u0531-\u0556\u10A0-\u10C5\u10C7\u10CD\u13A0-\u13F5\u1C90-\u1CBA\u1CBD-\u1CBF\u1E00\u1E02\u1E04\u1E06\u1E08\u1E0A\u1E0C\u1E0E\u1E10\u1E12\u1E14\u1E16\u1E18\u1E1A\u1E1C\u1E1E\u1E20\u1E22\u1E24\u1E26\u1E28\u1E2A\u1E2C\u1E2E\u1E30\u1E32\u1E34\u1E36\u1E38\u1E3A\u1E3C\u1E3E\u1E40\u1E42\u1E44\u1E46\u1E48\u1E4A\u1E4C\u1E4E\u1E50\u1E52\u1E54\u1E56\u1E58\u1E5A\u1E5C\u1E5E\u1E60\u1E62\u1E64\u1E66\u1E68\u1E6A\u1E6C\u1E6E\u1E70\u1E72\u1E74\u1E76\u1E78\u1E7A\u1E7C\u1E7E\u1E80\u1E82\u1E84\u1E86\u1E88\u1E8A\u1E8C\u1E8E\u1E90\u1E92\u1E94\u1E9E\u1EA0\u1EA2\u1EA4\u1EA6\u1EA8\u1EAA\u1EAC\u1EAE\u1EB0\u1EB2\u1EB4\u1EB6\u1EB8\u1EBA\u1EBC\u1EBE\u1EC0\u1EC2\u1EC4\u1EC6\u1EC8\u1ECA\u1ECC\u1ECE\u1ED0\u1ED2\u1ED4\u1ED6\u1ED8\u1EDA\u1EDC\u1EDE\u1EE0\u1EE2\u1EE4\u1EE6\u1EE8\u1EEA\u1EEC\u1EEE\u1EF0\u1EF2\u1EF4\u1EF6\u1EF8\u1EFA\u1EFC\u1EFE\u1F08-\u1F0F\u1F18-\u1F1D\u1F28-\u1F2F\u1F38-\u1F3F\u1F48-\u1F4D\u1F59\u1F5B\u1F5D\u1F5F\u1F68-\u1F6F\u1FB8-\u1FBB\u1FC8-\u1FCB\u1FD8-\u1FDB\u1FE8-\u1FEC\u1FF8-\u1FFB\u2102\u2107\u210B-\u210D\u2110-\u2112\u2115\u2119-\u211D\u2124\u2126\u2128\u212A-\u212D\u2130-\u2133\u213E\u213F\u2145\u2160-\u216F\u2183\u24B6-\u24CF\u2C00-\u2C2F\u2C60\u2C62-\u2C64\u2C67\u2C69\u2C6B\u2C6D-\u2C70\u2C72\u2C75\u2C7E-\u2C80\u2C82\u2C84\u2C86\u2C88\u2C8A\u2C8C\u2C8E\u2C90\u2C92\u2C94\u2C96\u2C98\u2C9A\u2C9C\u2C9E\u2CA0\u2CA2\u2CA4\u2CA6\u2CA8\u2CAA\u2CAC\u2CAE\u2CB0\u2CB2\u2CB4\u2CB6\u2CB8\u2CBA\u2CBC\u2CBE\u2CC0\u2CC2\u2CC4\u2CC6\u2CC8\u2CCA\u2CCC\u2CCE\u2CD0\u2CD2\u2CD4\u2CD6\u2CD8\u2CDA\u2CDC\u2CDE\u2CE0\u2CE2\u2CEB\u2CED\u2CF2\uA640\uA642\uA644\uA646\uA648\uA64A\uA64C\uA64E\uA650\uA652\uA654\uA656\uA658\uA65A\uA65C\uA65E\uA660\uA662\uA664\uA666\uA668\uA66A\uA66C\uA680\uA682\uA684\uA686\uA688\uA68A\uA68C\uA68E\uA690\uA692\uA694\uA696\uA698\uA69A\uA722\uA724\uA726\uA728\uA72A\uA72C\uA72E\uA732\uA734\uA736\uA738\uA73A\uA73C\uA73E\uA740\uA742\uA744\uA746\uA748\uA74A\uA74C\uA74E\uA750\uA752\uA754\uA756\uA758\uA75A\uA75C\uA75E\uA760\uA762\uA764\uA766\uA768\uA76A\uA76C\uA76E\uA779\uA77B\uA77D\uA77E\uA780\uA782\uA784\uA786\uA78B\uA78D\uA790\uA792\uA796\uA798\uA79A\uA79C\uA79E\uA7A0\uA7A2\uA7A4\uA7A6\uA7A8\uA7AA-\uA7AE\uA7B0-\uA7B4\uA7B6\uA7B8\uA7BA\uA7BC\uA7BE\uA7C0\uA7C2\uA7C4-\uA7C7\uA7C9\uA7D0\uA7D6\uA7D8\uA7F5\uFF21-\uFF3A\U00010400-\U00010427\U000104B0-\U000104D3\U00010570-\U0001057A\U0001057C-\U0001058A\U0001058C-\U00010592\U00010594\U00010595\U00010C80-\U00010CB2\U000118A0-\U000118BF\U00016E40-\U00016E5F\U0001D400-\U0001D419\U0001D434-\U0001D44D\U0001D468-\U0001D481\U0001D49C\U0001D49E\U0001D49F\U0001D4A2\U0001D4A5\U0001D4A6\U0001D4A9-\U0001D4AC\U0001D4AE-\U0001D4B5\U0001D4D0-\U0001D4E9\U0001D504\U0001D505\U0001D507-\U0001D50A\U0001D50D-\U0001D514\U0001D516-\U0001D51C\U0001D538\U0001D539\U0001D53B-\U0001D53E\U0001D540-\U0001D544\U0001D546\U0001D54A-\U0001D550\U0001D56C-\U0001D585\U0001D5A0-\U0001D5B9\U0001D5D4-\U0001D5ED\U0001D608-\U0001D621\U0001D63C-\U0001D655\U0001D670-\U0001D689\U0001D6A8-\U0001D6C0\U0001D6E2-\U0001D6FA\U0001D71C-\U0001D734\U0001D756-\U0001D76E\U0001D790-\U0001D7A8\U0001D7CA\U0001E900-\U0001E921\U0001F130-\U0001F149\U0001F150-\U0001F169\U0001F170-\U0001F189]"  # noqa: E501
# https://util.unicode.org/UnicodeJsps/list-unicodeset.jsp?a=%5B%3Alower%3A%5D&abb=on&ucd=on&esc=on
_RE_LOWERCASE = r"[a-z\u00AA\u00B5\u00BA\u00DF-\u00F6\u00F8-\u00FF\u0101\u0103\u0105\u0107\u0109\u010B\u010D\u010F\u0111\u0113\u0115\u0117\u0119\u011B\u011D\u011F\u0121\u0123\u0125\u0127\u0129\u012B\u012D\u012F\u0131\u0133\u0135\u0137\u0138\u013A\u013C\u013E\u0140\u0142\u0144\u0146\u0148\u0149\u014B\u014D\u014F\u0151\u0153\u0155\u0157\u0159\u015B\u015D\u015F\u0161\u0163\u0165\u0167\u0169\u016B\u016D\u016F\u0171\u0173\u0175\u0177\u017A\u017C\u017E-\u0180\u0183\u0185\u0188\u018C\u018D\u0192\u0195\u0199-\u019B\u019E\u01A1\u01A3\u01A5\u01A8\u01AA\u01AB\u01AD\u01B0\u01B4\u01B6\u01B9\u01BA\u01BD-\u01BF\u01C6\u01C9\u01CC\u01CE\u01D0\u01D2\u01D4\u01D6\u01D8\u01DA\u01DC\u01DD\u01DF\u01E1\u01E3\u01E5\u01E7\u01E9\u01EB\u01ED\u01EF\u01F0\u01F3\u01F5\u01F9\u01FB\u01FD\u01FF\u0201\u0203\u0205\u0207\u0209\u020B\u020D\u020F\u0211\u0213\u0215\u0217\u0219\u021B\u021D\u021F\u0221\u0223\u0225\u0227\u0229\u022B\u022D\u022F\u0231\u0233-\u0239\u023C\u023F\u0240\u0242\u0247\u0249\u024B\u024D\u024F-\u0293\u0295-\u02B8\u02C0\u02C1\u02E0-\u02E4\u0345\u0371\u0373\u0377\u037A-\u037D\u0390\u03AC-\u03CE\u03D0\u03D1\u03D5-\u03D7\u03D9\u03DB\u03DD\u03DF\u03E1\u03E3\u03E5\u03E7\u03E9\u03EB\u03ED\u03EF-\u03F3\u03F5\u03F8\u03FB\u03FC\u0430-\u045F\u0461\u0463\u0465\u0467\u0469\u046B\u046D\u046F\u0471\u0473\u0475\u0477\u0479\u047B\u047D\u047F\u0481\u048B\u048D\u048F\u0491\u0493\u0495\u0497\u0499\u049B\u049D\u049F\u04A1\u04A3\u04A5\u04A7\u04A9\u04AB\u04AD\u04AF\u04B1\u04B3\u04B5\u04B7\u04B9\u04BB\u04BD\u04BF\u04C2\u04C4\u04C6\u04C8\u04CA\u04CC\u04CE\u04CF\u04D1\u04D3\u04D5\u04D7\u04D9\u04DB\u04DD\u04DF\u04E1\u04E3\u04E5\u04E7\u04E9\u04EB\u04ED\u04EF\u04F1\u04F3\u04F5\u04F7\u04F9\u04FB\u04FD\u04FF\u0501\u0503\u0505\u0507\u0509\u050B\u050D\u050F\u0511\u0513\u0515\u0517\u0519\u051B\u051D\u051F\u0521\u0523\u0525\u0527\u0529\u052B\u052D\u052F\u0560-\u0588\u10D0-\u10FA\u10FC-\u10FF\u13F8-\u13FD\u1C80-\u1C88\u1D00-\u1DBF\u1E01\u1E03\u1E05\u1E07\u1E09\u1E0B\u1E0D\u1E0F\u1E11\u1E13\u1E15\u1E17\u1E19\u1E1B\u1E1D\u1E1F\u1E21\u1E23\u1E25\u1E27\u1E29\u1E2B\u1E2D\u1E2F\u1E31\u1E33\u1E35\u1E37\u1E39\u1E3B\u1E3D\u1E3F\u1E41\u1E43\u1E45\u1E47\u1E49\u1E4B\u1E4D\u1E4F\u1E51\u1E53\u1E55\u1E57\u1E59\u1E5B\u1E5D\u1E5F\u1E61\u1E63\u1E65\u1E67\u1E69\u1E6B\u1E6D\u1E6F\u1E71\u1E73\u1E75\u1E77\u1E79\u1E7B\u1E7D\u1E7F\u1E81\u1E83\u1E85\u1E87\u1E89\u1E8B\u1E8D\u1E8F\u1E91\u1E93\u1E95-\u1E9D\u1E9F\u1EA1\u1EA3\u1EA5\u1EA7\u1EA9\u1EAB\u1EAD\u1EAF\u1EB1\u1EB3\u1EB5\u1EB7\u1EB9\u1EBB\u1EBD\u1EBF\u1EC1\u1EC3\u1EC5\u1EC7\u1EC9\u1ECB\u1ECD\u1ECF\u1ED1\u1ED3\u1ED5\u1ED7\u1ED9\u1EDB\u1EDD\u1EDF\u1EE1\u1EE3\u1EE5\u1EE7\u1EE9\u1EEB\u1EED\u1EEF\u1EF1\u1EF3\u1EF5\u1EF7\u1EF9\u1EFB\u1EFD\u1EFF-\u1F07\u1F10-\u1F15\u1F20-\u1F27\u1F30-\u1F37\u1F40-\u1F45\u1F50-\u1F57\u1F60-\u1F67\u1F70-\u1F7D\u1F80-\u1F87\u1F90-\u1F97\u1FA0-\u1FA7\u1FB0-\u1FB4\u1FB6\u1FB7\u1FBE\u1FC2-\u1FC4\u1FC6\u1FC7\u1FD0-\u1FD3\u1FD6\u1FD7\u1FE0-\u1FE7\u1FF2-\u1FF4\u1FF6\u1FF7\u2071\u207F\u2090-\u209C\u210A\u210E\u210F\u2113\u212F\u2134\u2139\u213C\u213D\u2146-\u2149\u214E\u2170-\u217F\u2184\u24D0-\u24E9\u2C30-\u2C5F\u2C61\u2C65\u2C66\u2C68\u2C6A\u2C6C\u2C71\u2C73\u2C74\u2C76-\u2C7D\u2C81\u2C83\u2C85\u2C87\u2C89\u2C8B\u2C8D\u2C8F\u2C91\u2C93\u2C95\u2C97\u2C99\u2C9B\u2C9D\u2C9F\u2CA1\u2CA3\u2CA5\u2CA7\u2CA9\u2CAB\u2CAD\u2CAF\u2CB1\u2CB3\u2CB5\u2CB7\u2CB9\u2CBB\u2CBD\u2CBF\u2CC1\u2CC3\u2CC5\u2CC7\u2CC9\u2CCB\u2CCD\u2CCF\u2CD1\u2CD3\u2CD5\u2CD7\u2CD9\u2CDB\u2CDD\u2CDF\u2CE1\u2CE3\u2CE4\u2CEC\u2CEE\u2CF3\u2D00-\u2D25\u2D27\u2D2D\uA641\uA643\uA645\uA647\uA649\uA64B\uA64D\uA64F\uA651\uA653\uA655\uA657\uA659\uA65B\uA65D\uA65F\uA661\uA663\uA665\uA667\uA669\uA66B\uA66D\uA681\uA683\uA685\uA687\uA689\uA68B\uA68D\uA68F\uA691\uA693\uA695\uA697\uA699\uA69B-\uA69D\uA723\uA725\uA727\uA729\uA72B\uA72D\uA72F-\uA731\uA733\uA735\uA737\uA739\uA73B\uA73D\uA73F\uA741\uA743\uA745\uA747\uA749\uA74B\uA74D\uA74F\uA751\uA753\uA755\uA757\uA759\uA75B\uA75D\uA75F\uA761\uA763\uA765\uA767\uA769\uA76B\uA76D\uA76F-\uA778\uA77A\uA77C\uA77F\uA781\uA783\uA785\uA787\uA78C\uA78E\uA791\uA793-\uA795\uA797\uA799\uA79B\uA79D\uA79F\uA7A1\uA7A3\uA7A5\uA7A7\uA7A9\uA7AF\uA7B5\uA7B7\uA7B9\uA7BB\uA7BD\uA7BF\uA7C1\uA7C3\uA7C8\uA7CA\uA7D1\uA7D3\uA7D5\uA7D7\uA7D9\uA7F2-\uA7F4\uA7F6\uA7F8-\uA7FA\uAB30-\uAB5A\uAB5C-\uAB69\uAB70-\uABBF\uFB00-\uFB06\uFB13-\uFB17\uFF41-\uFF5A\U00010428-\U0001044F\U000104D8-\U000104FB\U00010597-\U000105A1\U000105A3-\U000105B1\U000105B3-\U000105B9\U000105BB\U000105BC\U00010780\U00010783-\U00010785\U00010787-\U000107B0\U000107B2-\U000107BA\U00010CC0-\U00010CF2\U000118C0-\U000118DF\U00016E60-\U00016E7F\U0001D41A-\U0001D433\U0001D44E-\U0001D454\U0001D456-\U0001D467\U0001D482-\U0001D49B\U0001D4B6-\U0001D4B9\U0001D4BB\U0001D4BD-\U0001D4C3\U0001D4C5-\U0001D4CF\U0001D4EA-\U0001D503\U0001D51E-\U0001D537\U0001D552-\U0001D56B\U0001D586-\U0001D59F\U0001D5BA-\U0001D5D3\U0001D5EE-\U0001D607\U0001D622-\U0001D63B\U0001D656-\U0001D66F\U0001D68A-\U0001D6A5\U0001D6C2-\U0001D6DA\U0001D6DC-\U0001D6E1\U0001D6FC-\U0001D714\U0001D716-\U0001D71B\U0001D736-\U0001D74E\U0001D750-\U0001D755\U0001D770-\U0001D788\U0001D78A-\U0001D78F\U0001D7AA-\U0001D7C2\U0001D7C4-\U0001D7C9\U0001D7CB\U0001DF00-\U0001DF09\U0001DF0B-\U0001DF1E\U0001DF25-\U0001DF2A\U0001E030-\U0001E06D\U0001E922-\U0001E943]"  # noqa: E501
_RE_LETTER = r"[A-Za-z" + _RE_UPPERCASE[4:-1] + _RE_LOWERCASE[4:-1] + r"]"

# https://www.fileformat.info/info/unicode/category/Sk/list.htm
_RE_MODIFIER = r"[\u005E\u0060\u00A8\u00AF\u00B4\u00B8\u02C2-\u02C5\u02D2\u02D3\u02D4-\u02D9\u02DA-\u02DF\u02E5-\u02FF\u0375\u0384\u0385\u0888\u1FBD\u1FBF-\u1FC1\u1FCD-\u1FCF\u1FDD-\u1FDF\u1FED\u1FEE\u1FEF\u1FFD\u1FFE\u309B\u309C\uA700-\uA716\uA720\uA721\uA789\uA78A\uAB5B\uAB6A\uAB6B\uFBB2-\uFBC2\uFF3E\uFF40\uFFE3]"

# https://www.fileformat.info/info/unicode/category/Pd/list.htm
_RE_DASH = r"[\u002D\u058A\u1806\u2010-\u2015\uFE58\uFE63\uFF0D]"
# https://www.fileformat.info/info/unicode/category/Zs/list.htm
_RE_SPACE = r"[\u0020\u00A0\u2000-\u200A\u202F\u205F\u3000]"
RE_SPACE = re.compile(_RE_SPACE)

RE_WHITESPACE = re.compile(r"[\n\t" + _RE_SPACE[1:-1] + r"]+")


def normalize_str(content):
    """
    Normalizira tekst za pohranu.
    """
    # U ovoj funkciji se može dodatno popraviti tekst (npr. ligature), no
    # ciljano samo mjenja <br/> sa razmacima jer su proizvedeni konverzijom PDFa
    # u HTML, tj. radi se o lossless pretvorbi ukoliko ih originalni rad nije
    # sadržao.

    # Bitno je samo da se ova fja ne primjenjuje na kontekst gdje ima smisla da
    # sadrži \n, \t ili nekoliko razmaka (npr. algoritam/kod).
    return RE_WHITESPACE.sub(" ", content.strip())


def _tag_value(tag, name, cast=None):
    value = tag.get(name)
    if cast is None:
        return value
    return value is not None and cast(value) or None

def tag_value(tag, attribute, inherited=True, cast=None):
    """
    Vrati vrijednost atributa za tag ili vrijednost na parentu.
    Ova funkcija pretpostavlja da se radi o atributu koji se nasljeđuje (CSS/stil).
    Ako ne uspije, vrati None.
    """
    if not inherited:
        return _tag_value(tag, attribute, cast)
    
    result = None
    while result is None:
        result = result or _tag_value(tag, attribute, cast)
        tag = tag.parent
        if tag is None:
            break
    return result

# kopija gornje funkcije, ali je ručno loop-unwrapana za bolje performanse
def tag_rect(tag):
    """
    Vrati bounding rect {x, y, w, h} od elementa ili parenta.
    Ako ne uspije, vrijednosti su None.
    """
    result = [None, None, None, None]


    while any(map(lambda it: it is None, result)):
        result[0] = result[0] or _tag_value(tag, "left", int)
        result[1] = result[1] or _tag_value(tag, "top", int)
        result[2] = result[2] or _tag_value(tag, "width", int)
        result[3] = result[3] or _tag_value(tag, "height", int)
        tag = tag.parent
        if tag is None:
            break

    return SimpleNamespace(x=result[0], y=result[1], w=result[2], h=result[3])


###########
# PARSERI #
###########


# RE_TITLE_FONT = re.compile(r"(Times|AdvPS|MyriadPro|STIX|MathPack|FranklinGothic)")

# Podešava minimalnu veličinu fonta naslova; obično se samo page# nalazi prije
MIN_TITLE_FONT_SIZE = 15


def is_title(tag):
    if not tag.name == "span" or tag.get("page") != "1":
        return False

    size = tag.get("font-size")
    if size is None or int(size) < MIN_TITLE_FONT_SIZE:
        return False

    # Font je velik wildcart, vjerujem da je "prvi veliki tekst" dovoljno
    # font = tag.get("font-family")
    # if font is None or not bool(RE_TITLE_FONT.search(font)):
    #     return False

    return True


def find_title(soup, context):
    title = soup.find(is_title)
    if title is not None:
        context["title-size"] = tag_value(title, "font-size", cast=int)
        return normalize_str(title.text)
    raise InsufficientParser("Title not found")

# treba paziti jer ovaj regex tehnički matcha bilo koju rečenicu koja sadrži
# znakove koji mogu biti u imenu
_RE_NAME_COMPONENT = r"[" + _RE_LETTER[1:-1] + _RE_MODIFIER[1:-1] + r"\." + _RE_DASH[1:-1] + r"]"
_RE_PREFIX_SKIP = r"(,|\u00b7)" + _RE_SPACE + r"+"
RE_AUTHOR_NAME = re.compile(
    r"(?:" + _RE_PREFIX_SKIP + r")?(" + _RE_NAME_COMPONENT + r"+(" + _RE_SPACE + _RE_NAME_COMPONENT + r"+" + r")+)"
)
RE_PREFIX_SKIP = re.compile( r"^" + _RE_PREFIX_SKIP)

def is_namelike(tag, context):
    # autori su uvijek sadržani u spanu na prvoj stranici
    if not tag.name == "span" or tag.get("page") != "1":
        return False

    # autori su uvijek navedeni prije datuma objave
    top = tag_value(tag, "top", cast=int)
    if top is None or top > context["date-start"]:
        return False

    # autori su uvijek veći od datuma i manji od naslova
    size = tag_value(tag, "font-size", cast=int)
    if size is None or size <= context["date-size"] or size >= context["title-size"]:
        return False

    content = tag.text.strip()
    if not content or len(content) == 0:
        return False

    return RE_AUTHOR_NAME.match(content)


def find_authors(soup, context):
    result = []

    for c in soup.find_all(lambda t: is_namelike(t, context)):
        name = RE_AUTHOR_NAME.search(c.text.strip())
        if c.text.strip() == "Æ":
            continue
        if len(name.groups()) >= 3:
            cleaned = c.text.strip()
            pos = RE_PREFIX_SKIP.search(cleaned)
            if pos is not None:
                start, end = pos.span()
                cleaned = cleaned[end:]
            result.append(cleaned)

    if len(result) > 0:
        return result
    
    raise InsufficientParser("Author not found")


def parse_dates(content):
    result = {}
    content = map(lambda it: it.strip(), content.split("/"))

    for c in content:
        phase = "published"
        c_lower = c.lower()
        if c_lower.startswith("received"):
            phase = "received"
        elif c_lower.startswith("accepted"):
            phase = "accepted"
        elif c_lower.startswith("published"):
            phase = "published"
        result[phase] = c.split(":")[1].strip()

    return result


DATE_KEYWORDS = [
    "received:",
    "accepted:",
    "published:",
    "published online:",
]


def find_dates(soup, context):
    for date in soup.find_all("span", {"page": "1"}):
        content = date.text.strip()
        lowered = content.lower()
        for begin in DATE_KEYWORDS:
            if lowered.startswith(begin):
                context["date-start"] = tag_value(date, "top", cast=int)
                context["date-size"] = tag_value(date, "font-size", cast=int)
                line = next(filter(lambda it: begin == it.lower()[:len(begin)], content.split("\n")))
                return parse_dates(line)
    raise InsufficientParser("Dates not found")


PARSERS = {
    "title": find_title,
    ("received", "accepted", "published"): find_dates,
    "authors": find_authors,
}

############
# IZVOĐAČI #
############

def store_recursive(frame, structured, row, parser_name, name, value, table_only=False, separator="."):
    """
    Sprema `name`: `value` par u `frame` i `structured`, te ispravno podržava
    liste, dictionaryje i dr. strukturirane podatke.
    """
    # pandas.json_normalize ne odvaja vrijednosti u listama, a ovako možemo
    # dodati podršku i za filtriranje i neke dodatne gluposti kako nam padnu na
    # pamet.
    # Jedino ne pazi na rekurzivne strukture, no njih ne koristimo.

    if value is None:
        return

    if type(value) is tuple:
        value = list(value)
    
    if type(value) is list:
        assert type(name) is str, f"can't crossproduct {type(name)} typed name and {type(value)} indices"
        frame.loc[row, name + f"{separator}length"] = int(len(value))
        for i, entry in enumerate(value):
            store_recursive(frame, structured, row, parser_name, f"{name}{separator}{i}", entry, True, separator)
        if not table_only:
            structured[name] = value
    elif type(value) is dict:
        if type(name) is tuple:
            for entry in list(name):
                store_recursive(frame, structured, row, parser_name, entry, value.get(entry, None), True, separator)
                if not table_only:
                    structured[entry] = value.get(entry, None)
        else:
            assert type(name) is str, f"'{str(parser_name)}' parser requires string key"
            for entry in value:
                store_recursive(frame, structured, row, parser_name, f"{name}{separator}{entry}", value.get(entry, None), True, separator)
            if not table_only:
                structured[name] = value
    elif type(name) is str:
        frame.loc[row, name] = value
        if not table_only:
            structured[name] = value
    else:
        raise Exception(f"can't store '{str(parser_name)}' parser result to non-str '{name}' column")

def handle_sample(path):
    """Obrađuje jedan PDF dokument i vraća rezultate u obliku DataFramea"""
    soup = pdf_soup(path)
    key = os.path.splitext(os.path.basename(path))[0]

    try:
        if Path(os.path.join(OUT_DIR, f"{key}.gen.csv")).is_file():
            print(f"Skipping {key} (already processed)")
            return (key, None, None)

        frame = pd.DataFrame()
        structured = {
            "document": key + ".pdf"
        }

        # ovdje je isto dobro mjesto za branchanje i paralelnu obradu, no već
        # smo iskoristili sve fizičke coreove branchanjem na osnovu ulaznih
        # datoteka
        context = {}

        for name, f in PARSERS.items():
            parser_name = f.__name__
            try:
                store_recursive(frame, structured, key, parser_name, name, f(soup, context))
            except InsufficientParser:
                print(f"Can't find '{parser_name}' value in {os.path.join(IN_DIR, key)}.pdf.html")
            except Exception:
                print(f"Error handling '{parser_name}' in {os.path.join(IN_DIR, key)}.pdf.html:")
                print(traceback.format_exc())

        return (key, frame, structured)
    except Exception:
        print(f"{key} failed:")
        print(traceback.format_exc())
        return (key, None, None)


def test_specific(files):
    os.makedirs(OUT_DIR, exist_ok=True)
    for file in files:
        checked = os.path.join(
            OUT_DIR, os.path.splitext(os.path.basename(file))[0] + ".gen.csv"
        )
        if Path(checked).is_file():
            # handle_sample ignorira input ako postoji csv output
            os.remove(checked)
        name, frame, structured = handle_sample(file)

        if frame is not None:
            frame.to_csv(os.path.join(OUT_DIR, name + ".gen.csv"))
            frame.to_excel(os.path.join(OUT_DIR, name + ".gen.xlsx"))
        if structured is not None:
            with open(os.path.join(OUT_DIR, name + ".gen.json"), "w") as json_file:
                json.dump(structured, json_file)
            with open(os.path.join(OUT_DIR, name + ".gen.pickle"), "wb") as pkl_file:
                pickle.dump(structured, pkl_file)


def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    tasks = glob.iglob(os.path.join(IN_DIR, "*.pdf"))

    frames = []

    # obrada zadataka u batchevima veličine WORKER_COUNT
    with ProcessPoolExecutor(max_workers=WORKER_COUNT) as executor:
        futures = {executor.submit(handle_sample, task): task for task in tasks}
        for future in as_completed(futures):
            name, frame, structured = future.result()

            base_path = os.path.join(OUT_DIR, name)
            if frame is not None:
                frames.append(base_path)
                frame.to_csv(base_path + ".gen.csv")
                frame.to_excel(base_path + ".gen.xlsx")
            if structured is not None:
                with open(base_path + ".gen.json", "w") as json_file:
                    json.dump(structured, json_file)
                with open(base_path + ".gen.pickle", "wb") as pkl_file:
                    pickle.dump(structured, pkl_file)

    if len(frames) <= 1:
        # sanity check, ne treba mergeat ništa jer se radi o jednom dokumentu
        return
    
    base_path = os.path.join(OUT_DIR, "merged")

    with open(base_path + ".json", "w") as json_file:
        json_file.write("[")
        if len(frames) > 1:
            for path in frames[:-1]:
                with open(path + ".gen.json", 'r') as it:
                    json_file.write(it.read())
                    json_file.write(", ")
        with open(frames[-1] + ".gen.json", 'r') as it:
            json_file.write(it.read())
        json_file.write("]")

    try:
        frame = pd.DataFrame()
        for path in frames:
            it = pd.read_csv(path + ".gen.csv", index_col=0)
            frame = pd.concat([frame, it], sort=False)
        frame.to_csv(base_path + ".csv")
        frame.to_excel(base_path + ".xlsx")
    except MemoryError:
        print("Can't generate merged csv & xlsx file - data too large to hold in memory")
        return

    try:
        all_data = []
        for path in frames:
            with open(path + ".gen.pickle", 'rb') as it:
                all_data.append(pickle.load(it))
        with open(base_path + ".pickle", "wb") as pkl_file:
            pickle.dump(all_data, pkl_file)
    except MemoryError:
        print("Can't generate merged pickle file - data too large to hold in memory")
        return

if __name__ == "__main__":
    if len(sys.argv) == 1:
        run()
    else:
        # ako se eksplicitno navede ime datoteke/a, onda ih sekvencijalno obradi
        # bez cacheanja. Korisno za debugganje individualnih slučajeva.
        test_specific(sys.argv[1:])
