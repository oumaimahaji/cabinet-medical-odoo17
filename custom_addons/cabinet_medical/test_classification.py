import os

def build_med_to_dci(data_dir):
    cis_file = os.path.join(data_dir, 'CIS_bdpm.txt')
    compo_file = os.path.join(data_dir, 'CIS_COMPO_bdpm.txt')

    cis_to_dci = {}
    with open(compo_file, 'r', encoding='latin-1') as f:
        for line in f:
            parts = line.strip('\n').split('\t')
            if len(parts) >= 4:
                cis = parts[0].strip()
                dci = parts[3].strip()
                type_substance = parts[6].strip() if len(parts) >= 7 else 'SA'
                if type_substance == 'SA':
                    if cis not in cis_to_dci:
                        cis_to_dci[cis] = set()
                    cis_to_dci[cis].add(dci)

    med_to_dci = {}
    with open(cis_file, 'r', encoding='latin-1') as f:
        for line in f:
            parts = line.strip('\n').split('\t')
            if len(parts) >= 2:
                cis = parts[0].strip()
                nom_commercial = parts[1].strip()
                if cis in cis_to_dci:
                    dcis_str = " + ".join(sorted(cis_to_dci[cis]))
                    med_to_dci[nom_commercial] = dcis_str

    return med_to_dci

def get_families_for_dci(dci):
    dci_upper = dci.upper()
    families = []
    
    # Règle pour les Macrolides
    macrolides = ["AZITHROMYCINE", "CLARITHROMYCINE", "ERYTHROMYCINE", "ÉRYTHROMYCINE", "ROXITHROMYCINE", "SPIRAMYCINE", "JOSAMYCINE"]
    for macrolide in macrolides:
        if macrolide in dci_upper:
            families.append("macrolide")
            break

    # Règle pour les Pénicillines (mise à jour)
    if "CILLINE" in dci_upper:
        families.append("penicilline")
        
    # Autres règles
    if "FLOXACINE" in dci_upper:
        families.append("quinolone")
    if dci_upper.endswith("CPHALOSPORINE") or dci_upper.endswith("CEPHALOSPORINE") or dci_upper.startswith("CEF") or dci_upper.startswith("CF"):
        families.append("cephalosporine")
    
    # Règle pour les Sulfamides
    words = dci_upper.split()
    for word in words:
        if word.startswith("SULFA") and "SULFATE" not in word and "SULFITE" not in word:
            families.append("sulfamide")
            break
            
    return families

if __name__ == '__main__':
    data_dir = r'c:\odoo - Copie\custom_addons\cabinet_medical\data'
    med_to_dci = build_med_to_dci(data_dir)
    
    unique_dcis = set()
    for dci_str in med_to_dci.values():
        for single_dci in dci_str.split(" + "):
            unique_dcis.add(single_dci.strip())

    # 1. Vérification des "CILLINE"
    cillines = [dci for dci in unique_dcis if "CILLINE" in dci.upper()]
    print("--- VÉRIFICATION DES DCI CONTENANT 'CILLINE' ---")
    for dci in sorted(cillines):
        print(f"  - {dci}")
    print("\n" + "="*50 + "\n")

    # Grouper par famille
    classified_groups = {}
    unclassified = []
    doublons = []

    for dci in sorted(unique_dcis):
        familles = get_families_for_dci(dci)
        if len(familles) > 0:
            if len(familles) > 1:
                doublons.append((dci, familles))
            for famille in familles:
                if famille not in classified_groups:
                    classified_groups[famille] = []
                classified_groups[famille].append(dci)
        else:
            unclassified.append(dci)

    total_classified = sum(len(items) for items in classified_groups.values())
    print(f"Total des DCI uniques extraites : {len(unique_dcis)}")
    print(f"DCI classées (incluant doublons) : {total_classified}")
    print(f"DCI NON classées : {len(unclassified)}")
    print(f"DCI dans PLUSIEURS familles (doublons) : {len(doublons)}\n")

    print("--- LISTE COMPLÈTE DES DCI CLASSÉS PAR FAMILLE ---")
    for famille, dcis in sorted(classified_groups.items()):
        print(f"\n>> FAMILLE : {famille.upper()} ({len(dcis)} substances)")
        for dci in dcis:
            print(f"  - {dci}")
            
    if doublons:
        print("\n--- DOUBLONS (DCI dans plusieurs familles) ---")
        for dci, fams in doublons:
            print(f"  - {dci} : {fams}")
