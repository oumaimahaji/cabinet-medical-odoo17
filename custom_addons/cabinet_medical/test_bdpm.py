import os

def build_med_to_dci(data_dir):
    cis_file = os.path.join(data_dir, 'CIS_bdpm.txt')
    compo_file = os.path.join(data_dir, 'CIS_COMPO_bdpm.txt')

    # 1. Mapping CIS -> list of DCI
    cis_to_dci = {}
    with open(compo_file, 'r', encoding='latin-1') as f:
        for line in f:
            parts = line.strip('\n').split('\t')
            if len(parts) >= 4:
                cis = parts[0].strip()
                # En BDPM, le champ 3 (4ème colonne) contient la substance (DCI)
                # Mais il y a aussi SA (Substance Active) vs FT (Fraction Thérapeutique)
                # Le type est dans la 7ème colonne (index 6) mais on peut juste prendre la substance
                dci = parts[3].strip()
                type_substance = parts[6].strip() if len(parts) >= 7 else 'SA'
                
                # On priorise les Substances Actives (SA) si possible, sinon on prend tout
                if type_substance == 'SA':
                    if cis not in cis_to_dci:
                        cis_to_dci[cis] = set()
                    cis_to_dci[cis].add(dci)

    # 2. Mapping Nom Commercial -> DCI
    med_to_dci = {}
    with open(cis_file, 'r', encoding='latin-1') as f:
        for line in f:
            parts = line.strip('\n').split('\t')
            if len(parts) >= 2:
                cis = parts[0].strip()
                # Nom commercial (ex: "AUGMENTIN 1 g/125 mg, poudre pour...")
                nom_commercial = parts[1].strip()
                
                if cis in cis_to_dci:
                    # On convertit le set de DCI en liste séparée par des '+ '
                    dcis_str = " + ".join(sorted(cis_to_dci[cis]))
                    med_to_dci[nom_commercial] = dcis_str

    return med_to_dci

if __name__ == '__main__':
    data_dir = r'c:\odoo - Copie\custom_addons\cabinet_medical\data'
    print("Construction du dictionnaire en cours...")
    med_to_dci = build_med_to_dci(data_dir)
    print(f"Dictionnaire construit avec succès ! Nombre de médicaments : {len(med_to_dci)}\n")

    print("--- EXEMPLES DE RÉSULTATS ---")
    augmentin_found = False
    doliprane_found = False

    for nom, dci in med_to_dci.items():
        nom_upper = nom.upper()
        if "AUGMENTIN" in nom_upper and not augmentin_found:
            print(f"- {nom}  ==>  DCI : {dci}")
            augmentin_found = True
        
        if "DOLIPRANE" in nom_upper and "1000" in nom_upper and not doliprane_found:
            print(f"- {nom}  ==>  DCI : {dci}")
            doliprane_found = True
            
        if augmentin_found and doliprane_found:
            break
