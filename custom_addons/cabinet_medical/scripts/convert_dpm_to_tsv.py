#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de conversion reproductible : liste_amm.xls (DPM Tunisie) -> liste_amm_tunisie.tsv (UTF-8)
Extrait les données officielles tunisiennes :
- Numéro AMM
- Nom commercial
- Dosage
- Forme
- DCI (Dénomination Commune Internationale)
- Classe thérapeutique
- Sous-classe
- Laboratoire
"""

import os
import sys
import unicodedata
import xlrd

def clean_str(val):
    if val is None:
        return ""
    if isinstance(val, float):
        # Pour les AMM ou dosages numériques
        if val.is_integer():
            return str(int(val)).strip()
        return str(val).strip()
    s = str(val).strip()
    # Remplacer les tabulations et retours à la ligne internes par des espaces
    s = s.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    # Normalisation Unicode NFC
    s = unicodedata.normalize('NFC', s)
    return " ".join(s.split())

def convert_xls_to_tsv(xls_path, tsv_path):
    if not os.path.exists(xls_path):
        raise FileNotFoundError(f"Fichier source introuvable : {xls_path}")
        
    print(f"[ETL DPM] Ouverture de {xls_path}...")
    wb = xlrd.open_workbook(xls_path)
    sheet = wb.sheet_by_index(0)
    
    header = [clean_str(sheet.cell_value(0, c)) for c in range(sheet.ncols)]
    print(f"[ETL DPM] Lignes totales : {sheet.nrows}, Colonnes : {sheet.ncols}")
    print(f"[ETL DPM] En-têtes détectés : {header}")
    
    # Mapping des colonnes
    col_map = {}
    for idx, col_name in enumerate(header):
        normalized = col_name.upper()
        if "NOM" in normalized and "COMMERCIAL" not in col_map:
            col_map["nom"] = idx
        elif "DOSAGE" in normalized and "dosage" not in col_map:
            col_map["dosage"] = idx
        elif "FORME" in normalized and "forme" not in col_map:
            col_map["forme"] = idx
        elif "DCI" in normalized and "dci" not in col_map:
            col_map["dci"] = idx
        elif "SOUS CLASSE" in normalized and "sous_classe" not in col_map:
            col_map["sous_classe"] = idx
        elif "CLASSE" in normalized and "classe" not in col_map and "SOUS" not in normalized:
            col_map["classe"] = idx
        elif "LABORATOIRE" in normalized and "laboratoire" not in col_map:
            col_map["laboratoire"] = idx
        elif normalized == "AMM" and "amm" not in col_map:
            col_map["amm"] = idx
        elif "AMM" in normalized and ("NUMÉRO" in normalized or "NUMERO" in normalized) and "amm" not in col_map:
            col_map["amm"] = idx

    print(f"[ETL DPM] Indices mappés : {col_map}")
    
    os.makedirs(os.path.dirname(os.path.abspath(tsv_path)), exist_ok=True)
    
    count_valid = 0
    count_multi_dci = 0
    with open(tsv_path, "w", encoding="utf-8") as out:
        out.write("amm\tnom\tdosage\tforme\tdci\tclasse\tsous_classe\tlaboratoire\n")
        
        for r in range(1, sheet.nrows):
            nom = clean_str(sheet.cell_value(r, col_map.get("nom", 0)))
            dci = clean_str(sheet.cell_value(r, col_map.get("dci", 4)))
            dosage = clean_str(sheet.cell_value(r, col_map.get("dosage", 1)))
            forme = clean_str(sheet.cell_value(r, col_map.get("forme", 2)))
            classe = clean_str(sheet.cell_value(r, col_map.get("classe", 5)))
            sous_classe = clean_str(sheet.cell_value(r, col_map.get("sous_classe", 6)))
            labo = clean_str(sheet.cell_value(r, col_map.get("laboratoire", 7)))
            amm = clean_str(sheet.cell_value(r, col_map.get("amm", 12)))
            
            if not nom and not dci:
                continue
                
            if "+" in dci or "/" in dci:
                count_multi_dci += 1
                
            out.write(f"{amm}\t{nom}\t{dosage}\t{forme}\t{dci}\t{classe}\t{sous_classe}\t{labo}\n")
            count_valid += 1
            
    print(f"[ETL DPM] Conversion réussie vers {tsv_path}")
    print(f"[ETL DPM] Spécialités exportées : {count_valid}")
    print(f"[ETL DPM] Spécialités à multi-DCI : {count_multi_dci}")

if __name__ == "__main__":
    src_xls = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Hajji\Downloads\liste_amm.xls"
    default_tsv = os.path.join(
        os.path.dirname(__file__), "..", "data", "liste_amm_tunisie.tsv"
    )
    dst_tsv = sys.argv[2] if len(sys.argv) > 2 else default_tsv
    convert_xls_to_tsv(src_xls, dst_tsv)
