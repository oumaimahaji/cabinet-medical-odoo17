import unittest
import os
import sys
from unittest.mock import MagicMock

addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(addon_dir)

# Simulation des imports Odoo
def mock_decorator(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    def wrapper(fn):
        return fn
    return wrapper

mock_odoo = MagicMock()
mock_odoo.modules.get_module_resource = lambda mod, *args: os.path.join(addon_dir, *args) if mod == 'cabinet_medical' else None

class MockModel:
    pass

mock_models = MagicMock()
mock_models.Model = MockModel
mock_models.AbstractModel = MockModel
mock_odoo.models = mock_models

mock_api = MagicMock()
mock_api.onchange = mock_decorator
mock_api.constrains = mock_decorator
mock_api.depends = mock_decorator
mock_api.model = mock_decorator
mock_api.model_create_multi = mock_decorator
mock_odoo.api = mock_api

def mock_selection(*args, **kwargs): return MagicMock()
mock_fields = MagicMock()
mock_fields.Selection = mock_selection
mock_fields.Char = MagicMock
mock_fields.Text = MagicMock
mock_fields.Date = MagicMock
mock_fields.Datetime = MagicMock
mock_fields.Boolean = MagicMock
mock_fields.Many2one = MagicMock
mock_fields.One2many = MagicMock
mock_fields.Integer = MagicMock
mock_fields.Binary = MagicMock

sys.modules['odoo'] = mock_odoo
sys.modules['odoo.modules'] = mock_odoo.modules
sys.modules['odoo.fields'] = mock_fields
sys.modules['odoo.models'] = mock_models
sys.modules['odoo.api'] = mock_api
sys.modules['odoo.exceptions'] = MagicMock()
sys.modules['odoo.exceptions'].ValidationError = type('ValidationError', (Exception,), {})
sys.modules['odoo.exceptions'].AccessError = type('AccessError', (Exception,), {})

import importlib.util
presc_path = os.path.join(addon_dir, 'models', 'prescription.py')
spec = importlib.util.spec_from_file_location("models.prescription", presc_path)
assert spec is not None and spec.loader is not None
prescription_module = importlib.util.module_from_spec(spec)
sys.modules["models.prescription"] = prescription_module
spec.loader.exec_module(prescription_module)

Prescription = prescription_module.Prescription
_classify_medicament_or_famille = prescription_module._classify_medicament_or_famille
_classify_medicament_all_familles = prescription_module._classify_medicament_all_familles
_get_bdpm_ontology = prescription_module._get_bdpm_ontology


class TestTunisianPharmacology(unittest.TestCase):
    """
    Validation unitaire de l'adaptation au contexte tunisien :
    - Couverture des spécialités tunisiennes DPM (SAIPH, ADWYA, TERIAK, OPALIA, MEDIS, etc.)
    - Préservation intacte de la reconnaissance BDPM
    - Non-classification des noms inconnus / placebos
    - Détection stricte des allergies sur spécialités tunisiennes
    - Détection des interactions et doublons thérapeutiques
    - Absence de faux positifs sur combinaisons sécurisées
    """

    @classmethod
    def setUpClass(cls):
        cls.med_to_family = _get_bdpm_ontology()
        cls.presc = Prescription()

    def test_reconnaissance_specialites_tunisiennes(self):
        """Vérifie la classification correcte des marques tunisiennes majeures."""
        cas_tunisie = {
            "Acamantine 625": "penicilline",
            "Acacipro 500": "quinolone",
            "Biclavor": "penicilline",
            "Inflamyl 250": "ibuprofene",
            "Nifluril": "ibuprofene",
            "Angiotec": "iec",
            "Ramitec 5": "iec",
            "Ator 20": "statine",
            "Axen": "ibuprofene",
            "Algibrex": "ibuprofene",
            "Statinel": "statine",
            "Cefutil": "cephalosporine",
            "Sertraline Opalia": "isrs",
            "Bromazepam Opalia": "benzodiazepine",
            "Aprovel 150": "ara2",
        }
        for med, expected_fam in cas_tunisie.items():
            fam = _classify_medicament_or_famille(med)
            self.assertEqual(fam, expected_fam, f"Échec de reconnaissance pour la spécialité tunisienne '{med}'")

    def test_preservation_specialites_bdpm(self):
        """Vérifie que les spécialités françaises / internationales restent parfaitement reconnues."""
        cas_bdpm = {
            "Augmentin": "penicilline",
            "Doliprane": "paracetamol",
            "Voltarène": "ibuprofene",
            "Coversyl": "iec",
            "Tahor": "statine",
            "Sintrom": "avk",
            "Xanax": "benzodiazepine",
            "Tramadol": "opioide",
        }
        for med, expected_fam in cas_bdpm.items():
            fam = _classify_medicament_or_famille(med)
            self.assertEqual(fam, expected_fam, f"Régression BDPM sur '{med}'")

    def test_non_reconnaissance_noms_inconnus(self):
        """Vérifie qu'un nom inconnu ou imaginaire n'est jamais faussement classifié."""
        inconnus = [
            "ProduitInconnuXYZ",
            "PlaceboGenerique 100",
            "PlanteNaturelleFictive",
            "XYZ123456",
        ]
        for med in inconnus:
            fam = _classify_medicament_or_famille(med)
            self.assertIsNone(fam, f"Faux positif de classification pour nom inconnu '{med}' -> {fam}")

    def test_allergies_specialites_tunisiennes(self):
        """Vérifie le déclenchement des alertes allergies sur médicaments tunisiens."""
        # Acamantine vs Allergie Pénicilline
        res_amox = self.presc._verifier_niveau_1(["Acamantine"], "Allergie aux pénicillines")
        self.assertTrue(len(res_amox) > 0, "Alerte allergie manquée pour Acamantine (Pénicilline)")

        # Acacipro vs Allergie Quinolone
        res_cipro = self.presc._verifier_niveau_1(["Acacipro"], "Allergie aux fluoroquinolones")
        self.assertTrue(len(res_cipro) > 0, "Alerte allergie manquée pour Acacipro (Quinolone)")

        # Inflamyl vs Allergie AINS
        res_ains = self.presc._verifier_niveau_1(["Inflamyl"], "Allergie aux anti-inflammatoires (AINS)")
        self.assertTrue(len(res_ains) > 0, "Alerte allergie manquée pour Inflamyl (AINS)")

    def test_absence_faux_positif_allergie(self):
        """Vérifie qu'aucune alerte allergie n'est levée pour un médicament non relié."""
        res = self.presc._verifier_niveau_1(["Doliprane"], "Allergie aux pénicillines")
        self.assertEqual(len(res), 0, "Faux positif allergie détecté entre Doliprane et Pénicilline")

    def test_interactions_specialites_tunisiennes(self):
        """Vérifie les interactions majeures impliquant des spécialités tunisiennes."""
        # 1. AVK (Sintrom) + AINS tunisien (Inflamyl)
        alertes_avk = self.presc._verifier_interactions_medicamenteuses(
            ["Inflamyl"],
            context_traitements=[{"medicament": "Sintrom", "source": "Chronique", "source_type": "chronique"}]
        )
        self.assertTrue(any(a.get('type') == 'interaction' for a in alertes_avk), "Interaction AVK + AINS tunisien non détectée")

        # 2. Spironolactone + IEC tunisien (Angiotec)
        alertes_iec = self.presc._verifier_interactions_medicamenteuses(
            ["Angiotec"],
            context_traitements=[{"medicament": "Spironolactone", "source": "Chronique", "source_type": "chronique"}]
        )
        self.assertTrue(any(a.get('type') == 'interaction' for a in alertes_iec), "Interaction IEC + Spironolactone non détectée")

        # 3. Doublon intra-ordonnance tunisien (Acamantine + Biclavor : 2 pénicillines)
        alertes_doublon = self.presc._verifier_interactions_medicamenteuses(
            ["Acamantine", "Biclavor"],
            context_traitements=[]
        )
        self.assertTrue(any(a.get('type') == 'doublon' for a in alertes_doublon), "Doublon thérapeutique pénicilline non détecté")

    def test_absence_faux_positif_interaction(self):
        """Vérifie qu'aucune fausse interaction n'est signalée sur des associations courantes sûres."""
        alertes_safe = self.presc._verifier_interactions_medicamenteuses(
            ["Doliprane"],
            context_traitements=[{"medicament": "Augmentin", "source": "Chronique", "source_type": "chronique"}]
        )
        self.assertEqual(len(alertes_safe), 0, "Fausse interaction détectée entre Doliprane et Augmentin")

    def test_termes_chimiques_generiques_negatifs(self):
        """
        Vérifie qu'aucun terme chimique générique ne déclenche à tort une famille pharmacologique.
        Cas critiques exigés : 'Acide folique', 'Acide citrique', 'Vitamine C', 'Eau pour injection'.
        """
        termes_negatifs = [
            "Acide folique",
            "Acide citrique",
            "Vitamine C",
            "Eau pour injection",
            "Eau pour preparation injectable",
            "Chlorhydrate de L-Arginine",
            "Vitamine D3",
            "Huile de paraffine",
        ]
        for t in termes_negatifs:
            fam = _classify_medicament_or_famille(t)
            self.assertIsNone(fam, f"Faux positif sur terme générique/non-ciblé '{t}' classifié à tort en '{fam}'")

    def test_multi_dci_associations_tunisiennes(self):
        """
        Vérifie le traitement correct des médicaments contenant plusieurs DCI réelles :
        - Paracétamol + Vitamine C : Paracétamol reconnu, Vitamine C non attribuée à tort au paracétamol.
        - Paracétamol + Codéine : Priorité clinique opioïde et reconnaissance des principes actifs.
        - Amoxicilline + Acide Clavulanique : Pénicilline reconnue.
        - Captopril + Hydrochlorothiazide : IEC reconnu.
        """
        # 1. Paracétamol + Vitamine C (Vitamine C seule ne doit PAS être classifiée en paracétamol)
        self.assertIsNone(_classify_medicament_or_famille("Vitamine C"))
        self.assertEqual(_classify_medicament_or_famille("Paracetamol"), "paracetamol")
        
        # 2. Amoxicilline + Acide Clavulanique (ex. ACAMANTINE / BICLAVOR)
        self.assertEqual(_classify_medicament_or_famille("Amoxicilline"), "penicilline")
        self.assertEqual(_classify_medicament_or_famille("Acamantine"), "penicilline")
        self.assertEqual(_classify_medicament_or_famille("Biclavor"), "penicilline")

        # 3. Association Captopril + Hydrochlorothiazide (ex. CAPTOLIREX)
        self.assertEqual(_classify_medicament_or_famille("Captopril"), "iec")

        # 4. Paracétamol + Codéine (les deux DCI sont indexées avec leur propre famille)
        self.assertEqual(_classify_medicament_or_famille("Codeine"), "opioide")
        self.assertEqual(_classify_medicament_or_famille("Paracetamol"), "paracetamol")

    def test_correction1_multi_dci_interaction_opioide_bzd(self):
        """Correction 1 : Association Paracetamol+Codeine + Xanax -> Détection Opioïde + BZD."""
        alertes = self.presc._verifier_interactions_medicamenteuses(["Paracetamol+Codeine", "Xanax"])
        inter_types = [a.get('type') for a in alertes]
        self.assertIn('interaction', inter_types, "L'interaction opioïde + benzodiazépine doit être détectée.")
        inter = next(a for a in alertes if a.get('type') == 'interaction')
        self.assertIn("Benzodiazépine + Opioïde", inter.get('titre', ''))

    def test_correction1_multi_dci_doublon_paracetamol(self):
        """Correction 1 : Association Paracetamol+Codeine + Doliprane -> Détection Doublon Paracétamol."""
        alertes = self.presc._verifier_interactions_medicamenteuses(["Paracetamol+Codeine", "Doliprane"])
        inter_types = [a.get('type') for a in alertes]
        self.assertIn('doublon', inter_types, "Le doublon paracétamol doit être détecté.")
        doublon = next(a for a in alertes if a.get('type') == 'doublon')
        self.assertIn("Paracétamol", doublon.get('titre', ''))

    def test_correction1_multi_dci_conservation_deux_familles_et_non_duplication(self):
        """Correction 1 : Conservation des deux familles distinctes et non-duplication des alertes."""
        fams = _classify_medicament_all_familles("Paracetamol+Codeine")
        self.assertIn("paracetamol", fams)
        self.assertIn("opioide", fams)

        # Prescription de 3 médicaments croisés : Paracetamol+Codeine, Xanax, Doliprane
        alertes = self.presc._verifier_interactions_medicamenteuses(["Paracetamol+Codeine", "Xanax", "Doliprane"])
        inter_count = sum(1 for a in alertes if a.get('type') == 'interaction')
        doublon_count = sum(1 for a in alertes if a.get('type') == 'doublon')
        self.assertEqual(inter_count, 1, "Exactement 1 alerte d'interaction attendue (Opioïde + BZD sans doublon d'alerte)")
        self.assertEqual(doublon_count, 1, "Exactement 1 alerte de doublon attendue (Paracétamol sans doublon d'alerte)")

    def test_correction2_statut_medicament_inconnu_non_verifie(self):
        """Correction 2 : Un médicament inconnu (PlaceboInconnu 500) doit retourner non_verifie et aucun faux 'safe'."""
        statut, message, notif = self.presc._fusionner_resultats_ia([], [], ["PlaceboInconnu 500"], False)
        self.assertEqual(statut, 'non_verifie', "Un médicament inconnu doit avoir le statut 'non_verifie'.")
        self.assertNotIn("Aucun risque allergique détecté", message, "Ne doit pas affirmer l'innocuité d'un médicament non répertorié.")
        self.assertIn("Médicament non reconnu", message)
        self.assertEqual(notif['type'], 'warning')

    def test_correction2_statut_medicament_reconnu_safe(self):
        """Correction 2 : Un médicament reconnu sans alerte conserve 'safe' avec mention des limites."""
        statut, message, notif = self.presc._fusionner_resultats_ia([], [], ["Doliprane 1000mg"], "Pénicilline")
        self.assertEqual(statut, 'safe')
        self.assertIn("Aucun risque allergique détecté", message)
        self.assertEqual(notif['type'], 'success')

    def test_correction2_medicament_reconnu_avec_alerte_allergique(self):
        """Correction 2 : Un médicament reconnu avec risque allergique doit déclencher 'allergy_risk'."""
        alertes_n1 = self.presc._verifier_niveau_1(["Augmentin"], "Allergie aux pénicillines")
        statut, message, notif = self.presc._fusionner_resultats_ia(alertes_n1, [], ["Augmentin"], "Allergie aux pénicillines")
        self.assertEqual(statut, 'allergy_risk')
        self.assertIn("ALERTE ALLERGIE", message)

    def test_correction2_medicament_reconnu_avec_interaction(self):
        """Correction 2 : Un médicament reconnu impliqué dans une interaction doit déclencher 'allergy_risk'."""
        alertes_inter = self.presc._verifier_interactions_medicamenteuses(["Angiotec", "Aldactone"])
        statut, message, notif = self.presc._fusionner_resultats_ia([], [], ["Angiotec", "Aldactone"], False, alertes_interactions=alertes_inter)
        self.assertEqual(statut, 'allergy_risk')
        self.assertIn("ALERTES PHARMACOLOGIQUES", message)


if __name__ == '__main__':
    unittest.main()
