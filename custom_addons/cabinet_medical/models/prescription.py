import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

from odoo import models, fields, api  # type: ignore
import unicodedata
from odoo.exceptions import ValidationError, AccessError  # type: ignore
from datetime import date, datetime, timedelta
import re
import difflib
import hashlib
from odoo.modules import get_module_resource  # type: ignore
from types import MappingProxyType
from typing import Any
import threading


# -------------------------------------------------------------------------
# CONSTANTES & BASE DE CONNAISSANCES PHARMACOLOGIQUES
# -------------------------------------------------------------------------

# Modèles & Actions
PRESCRIPTION_MODEL = 'cabinet.prescription'
PRESCRIPTION_LINE_MODEL = 'cabinet.prescription.line'
CONSULTATION_MODEL = 'cabinet.consultation'
NOTIFICATION_MODEL = 'cabinet.notification'
ACTION_ACT_WINDOW = 'ir.actions.act_window'
ACTION_WINDOW_CLOSE = 'ir.actions.act_window_close'
DATE_FORMAT = '%d/%m/%Y'

# Rôles & Sécurité
GROUP_MEDECIN = 'cabinet_medical.group_medecin'

# Clés de dictionnaires (Interactions, Détections, Notifications)
KEY_TYPE = 'type'
KEY_GRAVITE = 'gravite'
KEY_TITRE = 'titre'
KEY_RAISON = 'raison'
KEY_FAMILLE_A = 'famille_a'
KEY_FAMILLE_B = 'famille_b'
KEY_MEDICAMENT = 'medicament'
KEY_MEDICAMENT_A = 'medicament_a'
KEY_MEDICAMENT_B = 'medicament_b'
KEY_FAMILLE = 'famille'
KEY_SOURCE = 'source'
KEY_SOURCE_TYPE = 'source_type'
KEY_SCORE = 'score'
KEY_TITLE = 'title'
KEY_MESSAGE = 'message'
KEY_CONTEXTE = 'contexte'
KEY_TYPE_LABEL = 'type_label'
KEY_DUREE = 'duree'
KEY_IS_ACTIVE = 'is_active'
KEY_DATE_PRESCRIPTION = 'date_prescription'

# Types d'alertes & Niveaux de gravité
TYPE_INTERACTION = 'interaction'
TYPE_ALLERGIE = 'allergie'
TYPE_DOUBLON = 'doublon'
GRAVITE_MAJEURE = 'majeure'
GRAVITE_MODEREE = 'moderee'

LEVEL_DANGER = 'danger'
LEVEL_WARNING = 'warning'
LEVEL_INFO = 'info'
LEVEL_SUCCESS = 'success'

# États & Statuts de prescription / IA
STATE_DRAFT = 'draft'
STATE_SIGNED = 'signed'

IA_STATUT_NON_VERIFIE = 'non_verifie'
IA_STATUT_SAFE = 'safe'
IA_STATUT_ALLERGY_RISK = 'allergy_risk'

FIELD_STATE = 'state'
FIELD_ACTIVE = 'active'
FIELD_MEDICAMENT = 'medicament'
FIELD_POSOLOGIE = 'posologie'
FIELD_DOSAGE = 'dosage'
FIELD_DUREE = 'duree'
FIELD_PRESCRIPTION_ID = 'prescription_id'
FIELD_IA_STATUT = 'ia_statut'
FIELD_IA_MESSAGE = 'ia_message'
FIELD_IA_FINGERPRINT = 'ia_fingerprint'
FIELD_IA_VERIFIED_BY_USER = 'ia_verified_by_user'
FIELD_ORDONNANCE_LINE_IDS = 'ordonnance_line_ids'
FIELD_PATIENT_ID = 'patient_id'
FIELD_DATE_PRESCRIPTION = 'date_prescription'
FIELD_IS_VALIDATED = 'is_validated'
FIELD_IS_IA_TEMPORARY_DRAFT = 'is_ia_temporary_draft'
FIELD_IN_SIGNATURE_PROCESS = 'in_signature_process'

# Familles pharmacologiques
FAMILLE_PENICILLINE = 'penicilline'
FAMILLE_ASPIRINE = 'aspirine'
FAMILLE_IBUPROFENE = 'ibuprofene'
FAMILLE_PARACETAMOL = 'paracetamol'
FAMILLE_SULFAMIDE = 'sulfamide'
FAMILLE_MACROLIDE = 'macrolide'
FAMILLE_QUINOLONE = 'quinolone'
FAMILLE_CEPHALOSPORINE = 'cephalosporine'

FAMILLE_IEC = 'iec'
FAMILLE_ARA2 = 'ara2'
FAMILLE_DIURETIQUE_EPARGNEUR_POTASSIUM = 'diuretique_epargneur_potassium'
FAMILLE_AVK = 'avk'
FAMILLE_AINS = 'ains'
FAMILLE_STATINE = 'statine'
FAMILLE_ISRS = 'isrs'
FAMILLE_BENZODIAZEPINE = 'benzodiazepine'
FAMILLE_OPIOIDE = 'opioide'
FAMILLE_CORTICOIDE = 'corticoide'
FAMILLE_METHOTREXATE = 'methotrexate'
FAMILLE_LITHIUM = 'lithium'
FAMILLE_DIGOXINE = 'digoxine'
FAMILLE_AMIODARONE = 'amiodarone'

FAMILLES_ALLERGIES = {
    FAMILLE_PENICILLINE: [
        "penicilline", "pénicilline", "penecilline", "peniciline", "penicillin", "pénicillines", "penicillines", "penecillines",
        "amoxicilline", "amoxcilline", "amoxycilline", "amoxicillina", "amoxicillin", "amox", "amoxil",
        "augmentin", "clamoxyl", "ampicilline", "oxacilline", "cloxacilline", "piperacilline", "ticarcilline",
        "betalactamines", "bétalactamines", "betalactamine", "bétalactamine", "beta-lactamines", "beta lactamine", "beta-lactame",
        "choc penicilline", "reaction penicilline", "allergie penicilline",
        "بنسلين", "البنسلين", "أموكسيسيلين", "اموكسيسيلين", "أوجمنتين", "اوجمنتين", "كلاموكسيل", "مضاد حيوي بنسلين"
    ],
    FAMILLE_ASPIRINE: [
        "acide acetylsalicylique", "acide acétylsalicylique", "aspirine", "aspirin", "aspegic", "aspégic", "kardegic", "kardégic", "salicyle", "salicylates",
        "salicylate", "intolerance aspirine", "allergie aspirine", "reaction aspirine",
        "أسبرين", "الأسبرين", "اسبرين"
    ],
    FAMILLE_IBUPROFENE: [
        "ibuprofene", "ibuprofène", "ibuprofen", "advil", "nurofen", "upfen", "antarene", "antarène", "ketoprofene", "kétoprofène", "profanid", "profenid", "flurbiprofene",
        "ains", "anti-inflammatoire", "anti-inflammatoires", "anti inflammatoire", "anti inflammatoires", "antiinflammatoire", "antiinflammatoires",
        "intolerance aux ains", "intolerance ains", "allergie anti-inflammatoire", "allergie aux ains", "reaction anti-inflammatoire",
        "أيبوبروفين", "ايبوبروفين", "بروفين", "مضاد التهاب"
    ],
    FAMILLE_PARACETAMOL: [
        "paracetamol", "paracétamol", "paracetamolum", "acetaminophen", "acétaminophène", "doliprane", "dafalgan", "efferalgan", "panadol", "perfalgan",
        "intolerance paracetamol", "allergie paracetamol", "reaction doliprane", "allergie doliprane",
        "باراسيتامول", "الباراسيتامول", "دولبران", "بانادول"
    ],
    FAMILLE_SULFAMIDE: [
        "sulfamide", "sulfamides", "sulfonamide", "sulfonamides", "bactrim", "sulfamethoxazole", "sulfadiazine", "cotrimoxazole",
        "allergie sulfamides", "reaction sulfamide", "intolerance sulfamides", "allergie bactrim",
        "سلفاميد", "السلفاميد"
    ],
    FAMILLE_MACROLIDE: [
        "macrolide", "macrolides", "azithromycine", "clarithromycine", "erythromycine", "érythromycine", "josamycine", "spiramycine", "zithromax", "rovamycine", "zeclar",
        "allergie macrolides", "reaction macrolide",
        "ماكروليد", "أزيثروميسين", "ازيثروميسين"
    ],
    FAMILLE_QUINOLONE: [
        "quinolone", "quinolones", "fluoroquinolone", "fluoroquinolones", "ciprofloxacine", "levofloxacine", "lévofloxacine", "ofloxacine", "ciflox", "tavanic", "norfloxacine",
        "allergie quinolones", "reaction fluoroquinolone",
        "كينولون", "سيبروفلوكساسين"
    ],
    FAMILLE_CEPHALOSPORINE: [
        "cephalosporine", "céphalosporine", "cephalosporines", "céphalosporines", "ceftriaxone", "cefixime", "céfixime", "cefuroxime", "céfuroxime", "rocephine", "rocéphine", "oroken", "cefotaxime", "keforal",
        "allergie cephalosporines", "reaction cephalosporine",
        "سيفالوسبورين", "سفترياكسون"
    ],
}

CLASSES_PHARMACOLOGIQUES = {
    FAMILLE_IEC: [
        "ramipril", "triatec", "altace",
        "captopril", "lopril", "capoten",
        "enalapril", "énalapril", "renitec", "vasotec",
        "perindopril", "périndopril", "coversyl", "acetal",
        "lisinopril", "prinivil", "zestril",
        "benazepril", "bénazépril", "cibacene", "lotensin",
        "fosinopril", "fozitec", "monopril",
        "quinapril", "acuitel", "accupro",
        "zofenopril", "zofénopril", "zopranol",
        "trandolapril", "odrik", "gopten",
        "iec", "inhibiteur de l'enzyme de conversion", "inhibiteurs de l'enzyme de conversion",
        "راميبريل", "كابتوبريل", "إنالابريل", "بيريندوبريل", "ليسينوبريل"
    ],
    FAMILLE_ARA2: [
        "losartan", "cozaar",
        "valsartan", "tareg", "diovan",
        "candesartan", "candésartan", "atacand", "kenzen",
        "irbesartan", "irbésartan", "aprovel", "avapro",
        "telmisartan", "micardis", "pritor",
        "olmesartan", "olmésartan", "olmetec", "benicar",
        "eprosartan", "éprosartan", "teveten",
        "azilsartan", "edarbi",
        "sartan", "sartans", "ara2", "araii", "ara ii", "antagoniste des recepteurs de l'angiotensine",
        "لوسارتان", "فالسارتان", "كانديسارتان", "إربيسارتان", "تيلميسارتان"
    ],
    FAMILLE_DIURETIQUE_EPARGNEUR_POTASSIUM: [
        "spironolactone", "aldactone", "spironone",
        "eplerenone", "éplérénone", "inspra",
        "amiloride", "modamide",
        "triamterene", "triamtérène", "teriam",
        "canrenone", "canrénone", "phanurane",
        "diuretique epargneur de potassium", "diuretiques epargneurs de potassium", "epargneur de potassium", "anti-aldosterone", "antialdosterone",
        "سبيرونولاكتون", "إبليرينون", "أميلوريد"
    ],
    FAMILLE_AVK: [
        "warfarine", "coumadine", "marevan", "jantoven",
        "fluindione", "previscan", "préviscan",
        "acenocoumarol", "acénocoumarol", "sintrom", "sinthrome",
        "phenindione", "phénindione", "pindione",
        "dabigatran", "pradaxa", "rivaroxaban", "xarelto", "apixaban", "eliquis", "edoxaban", "lixiana",
        "avk", "antivitamine k", "antivitamines k", "anticoagulant oral", "anticoagulants oraux", "anticoagulant", "anticoagulants",
        "وارفارين", "سينتروم", "بريفيسكان", "مضاد تخثر"
    ],
    FAMILLE_AINS: [
        "ibuprofene", "ibuprofène", "ibuprofen", "advil", "nurofen", "upfen", "antarene", "antarène", "brufen",
        "ketoprofene", "kétoprofène", "ketoprofen", "profenid", "profanid", "bi-profenid", "biprofenid", "toprec", "ketum",
        "diclofenac", "diclofénac", "voltarene", "voltarène", "cataflam", "dicloreum", "flector",
        "naproxene", "naproxène", "naprosyn", "apranax", "aleve",
        "celecoxib", "célécoxib", "celebrex",
        "etoricoxib", "étoricoxib", "arcoxia",
        "meloxicam", "méloxicam", "mobic",
        "piroxicam", "feldene", "feldène",
        "indometacine", "indométacine", "indocid", "chrono-indocid",
        "flurbiprofene", "flurbiprofène", "antalcalm", "cebesine", "cebutid",
        "acide tiaprofenique", "acide tiaprofénique", "surgam",
        "ains", "anti-inflammatoire non steroidien", "anti-inflammatoires non steroidiens", "anti inflammatoire non steroidien",
        "إيبوبروفين", "كيتوبروفين", "ديكلوفيناك", "نابروكسين", "مضاد التهاب"
    ],
    FAMILLE_STATINE: [
        "atorvastatine", "tahor", "lipitor",
        "simvastatine", "zocor", "lodales", "simvax",
        "rosuvastatine", "rosuvastatine", "crestor",
        "pravastatine", "elisor", "vasten", "pravachol",
        "fluvastatine", "fractal", "lescol",
        "pitavastatine", "livazo",
        "lovastatine", "mevacor",
        "statine", "statines", "inhibiteur hmg-coa",
        "أتورفاستاتين", "سيمفاستاتين", "روزوفاستاتين", "ستاتين"
    ],
    FAMILLE_ISRS: [
        "fluoxetine", "fluoxétine", "prozac",
        "sertraline", "zoloft",
        "paroxetine", "paroxétine", "deroxat", "deroxate", "paxil", "divarius",
        "citalopram", "seropram", "celexa",
        "escitalopram", "escitaloprame", "seroplex", "sipralexa", "lexapro",
        "fluvoxamine", "floxyfral", "luvox",
        "isrs", "irss", "antidepresseur isrs", "inhibiteur selectif de la recapture de la serotonine",
        "فلوكسيتين", "سيرترالين", "باروكسيتين", "سيتالوبرام", "إسيتالوبرام", "مضاد اكتئاب"
    ],
    FAMILLE_BENZODIAZEPINE: [
        "alprazolam", "xanax", "alprax",
        "diazepam", "diazépam", "valium",
        "lorazepam", "lorazépam", "temesta", "témesta", "ativan",
        "bromazepam", "bromazépam", "lexomil", "lectopam",
        "prazepam", "prazépam", "lysanxia",
        "clonazepam", "clonazépam", "rivotril", "klonopin",
        "oxazepam", "oxazépam", "seresta",
        "clobazam", "urbanyl",
        "clorazepate", "clorazépate", "tranxene", "tranxène",
        "nordazepam", "nordazépam", "nordaz",
        "zolpidem", "stilnox", "ambien",
        "zopiclone", "imovane",
        "benzodiazepine", "benzodiazépine", "benzodiazepines", "benzodiazépines", "bzd", "anxiolytique",
        "ألبرازولام", "ديازيبام", "لورازيبام", "برومازيبام", "كلونازيبام", "زولبيديم", "بنزوديازيبين"
    ],
    FAMILLE_OPIOIDE: [
        "tramadol", "topalgic", "contramal", "zamadol", "monoalgic",
        "ixprim", "zaldiar",
        "codeine", "codéine", "codoliprane", "dafalgan codeine", "efferalgan codeine", "paderyl", "neocodion",
        "morphine", "skenan", "moscontin", "actiskenan", "sevredol",
        "fentanyl", "durogesic", "abstral", "actiq", "effentora", "instanyl", "fentanil",
        "oxycodone", "oxycontin", "oxynorm",
        "hydromorphone", "sophidone",
        "buprenorphine", "buprénorphine", "subutex", "temgesic",
        "methadone", "méthadone",
        "tapentadol", "palexia",
        "opioide", "opioïde", "opioides", "opioïdes", "morphinique", "morphiniques", "antalgique palier 2", "antalgique palier 3", "derive morphinique",
        "ترامادول", "كودايين", "مورفين", "فينتانيل", "أوكسيكودون", "أفيونيات"
    ],
    FAMILLE_CORTICOIDE: [
        "prednisone", "cortancyl",
        "prednisolone", "solupred",
        "methylprednisolone", "méthylprednisolone", "medrol", "médrol", "solu-medrol",
        "dexamethasone", "dexaméthasone", "decadron", "soludecadron",
        "betamethasone", "bétaméthasone", "celestene", "célestène",
        "hydrocortisone",
        "corticoide", "corticoïde", "corticoides", "corticoïdes", "corticosteroide", "corticostéroïde",
        "بريدنيزون", "بريدنيزولون", "ديكساميثازون", "بيتاميثازون", "كورتيزون"
    ],
    FAMILLE_METHOTREXATE: [
        "methotrexate", "méthotrexate", "novatrex", "metoject", "imeth", "ledertrexate",
        "ميثوتريكسات"
    ],
    FAMILLE_LITHIUM: [
        "lithium", "teralithe", "téralithe", "carbonate de lithium", "gluconate de lithium",
        "ليثيوم"
    ],
    FAMILLE_DIGOXINE: [
        "digoxine", "digoxin", "digoxine nativelle", "hemigoxine",
        "ديجوكسين"
    ],
    FAMILLE_AMIODARONE: [
        "amiodarone", "cordarone", "amiofar",
        "أميودارون"
    ]
}

INTERACTIONS_MEDICAMENTEUSES = [
    {
        KEY_FAMILLE_A: FAMILLE_IEC,
        KEY_FAMILLE_B: FAMILLE_DIURETIQUE_EPARGNEUR_POTASSIUM,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "IEC + Diurétique épargneur de potassium",
        KEY_RAISON: "Risque d'hyperkaliémie sévère potentiellement mortelle (synergie sur la rétention potassique rénale).",
    },
    {
        KEY_FAMILLE_A: FAMILLE_ARA2,
        KEY_FAMILLE_B: FAMILLE_DIURETIQUE_EPARGNEUR_POTASSIUM,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "ARA2 + Diurétique épargneur de potassium",
        KEY_RAISON: "Risque d'hyperkaliémie sévère potentiellement mortelle (synergie sur la rétention potassique rénale).",
    },
    {
        KEY_FAMILLE_A: FAMILLE_AVK,
        KEY_FAMILLE_B: FAMILLE_AINS,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Anticoagulant (AVK/AOD) + AINS",
        KEY_RAISON: "Majoration majeure du risque hémorragique (lésions muqueuses gastro-intestinales et inhibition de l'agrégation plaquettaire).",
    },
    {
        KEY_FAMILLE_A: FAMILLE_IEC,
        KEY_FAMILLE_B: FAMILLE_ARA2,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "IEC + ARA2 (Double blocage du SRAA)",
        KEY_RAISON: "Double blocage du système rénine-angiotensine contre-indiqué : risque accru d'hypotension artérielle sévère, d'hyperkaliémie et d'insuffisance rénale aiguë.",
    },
    {
        KEY_FAMILLE_A: FAMILLE_MACROLIDE,
        KEY_FAMILLE_B: FAMILLE_STATINE,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Macrolide + Statine",
        KEY_RAISON: "Inhibition enzymatique majeure du CYP3A4 : augmentation des concentrations plasmatiques de la statine avec risque élevé de rhabdomyolyse et de toxicité musculaire sévère.",
    },
    {
        KEY_FAMILLE_A: FAMILLE_ISRS,
        KEY_FAMILLE_B: FAMILLE_AINS,
        KEY_GRAVITE: GRAVITE_MODEREE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Antidépresseur ISRS + AINS",
        KEY_RAISON: "Augmentation du risque de saignement gastro-intestinal par synergie sur l'hémostase primaire (inhibition de la recapture plaquettaire de sérotonine + effet antiagrégant/ulcérogène des AINS).",
    },
    {
        KEY_FAMILLE_A: FAMILLE_BENZODIAZEPINE,
        KEY_FAMILLE_B: FAMILLE_OPIOIDE,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Benzodiazépine + Opioïde",
        KEY_RAISON: "Risque majeur de dépression respiratoire sévère, sédation profonde, coma et décès par effet dépresseur central synergique.",
    },
    {
        KEY_FAMILLE_A: FAMILLE_METHOTREXATE,
        KEY_FAMILLE_B: FAMILLE_AINS,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Méthotrexate + AINS",
        KEY_RAISON: "Diminution de l'excrétion rénale du méthotrexate par les AINS : risque de toxicité hématologique grave et de néphrotoxicité aiguë.",
    },
    {
        KEY_FAMILLE_A: FAMILLE_LITHIUM,
        KEY_FAMILLE_B: FAMILLE_AINS,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Lithium + AINS",
        KEY_RAISON: "Diminution de la clairance rénale du lithium par les AINS : augmentation de la lithémie pouvant atteindre des seuils toxiques (neurotoxicité, insuffisance rénale).",
    },
    {
        KEY_FAMILLE_A: FAMILLE_QUINOLONE,
        KEY_FAMILLE_B: FAMILLE_CORTICOIDE,
        KEY_GRAVITE: GRAVITE_MODEREE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Fluoroquinolone + Corticoïde",
        KEY_RAISON: "Majoration significative du risque de tendinopathie et de rupture du tendon d'Achille.",
    },
    {
        KEY_FAMILLE_A: FAMILLE_DIGOXINE,
        KEY_FAMILLE_B: FAMILLE_AMIODARONE,
        KEY_GRAVITE: GRAVITE_MODEREE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Digoxine + Amiodarone",
        KEY_RAISON: "Inhibition de la P-glycoprotéine et réduction de la clairance rénale de la digoxine : risque accru d'intoxication digitalique (nausées, troubles du rythme ventriculaire).",
    },
    {
        KEY_FAMILLE_A: FAMILLE_DIGOXINE,
        KEY_FAMILLE_B: FAMILLE_MACROLIDE,
        KEY_GRAVITE: GRAVITE_MODEREE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Digoxine + Macrolide",
        KEY_RAISON: "Inactivation de la flore intestinale inactivatrice de la digoxine par les macrolides : élévation de la digoxinémie et risque de toxicité.",
    },
    {
        KEY_FAMILLE_A: FAMILLE_AVK,
        KEY_FAMILLE_B: FAMILLE_ASPIRINE,
        KEY_GRAVITE: GRAVITE_MAJEURE,
        KEY_TYPE: TYPE_INTERACTION,
        KEY_TITRE: "Anticoagulant (AVK/AOD) + Aspirine",
        KEY_RAISON: "Majoration très importante du risque hémorragique par double inhibition de la coagulation et de l'agrégation plaquettaire.",
    },
]

FAMILLES_ANTIBIOTIQUES = {FAMILLE_PENICILLINE, FAMILLE_CEPHALOSPORINE, FAMILLE_MACROLIDE, FAMILLE_QUINOLONE, FAMILLE_SULFAMIDE}
TERMES_GENERIQUE_ANTIBIO = {"antibiotique", "antibiotiques", "antibio", "antibios", "مضاد حيوي"}

_BDPM_CACHE = None
_BDPM_LOCK = threading.Lock()
_TRANSFORMER_MODEL = None
_SENTENCE_TRANSFORMER_LIB = None
_TRANSFORMER_LOCK = threading.Lock()


def _get_transformer_model():
    """
    Charge et retourne en cache mémoire global (Singleton Thread-Safe Lazy Loading) le modèle Transformer NLP.
    Le chargement s'effectue à la demande lors du premier appel, avec PyTorch limité à 1 thread
    pour ne pas saturer le processeur ni perturber les requêtes HTTP d'Odoo.
    """
    global _TRANSFORMER_MODEL, _SENTENCE_TRANSFORMER_LIB
    if _TRANSFORMER_MODEL is not None and _SENTENCE_TRANSFORMER_LIB is not None:
        return _TRANSFORMER_MODEL, _SENTENCE_TRANSFORMER_LIB

    with _TRANSFORMER_LOCK:
        if _TRANSFORMER_MODEL is None or _SENTENCE_TRANSFORMER_LIB is None:
            try:
                from sentence_transformers import SentenceTransformer, util
                import torch

                try:
                    torch.set_num_threads(1)
                except Exception:
                    pass

                try:
                    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', local_files_only=True)
                except Exception:
                    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

                # Warmup CPU pour pré-compiler les graphes PyTorch
                with torch.no_grad():
                    model.encode(['warmup test'], convert_to_tensor=True)

                _TRANSFORMER_MODEL = model
                _SENTENCE_TRANSFORMER_LIB = (util, torch)
            except Exception:
                pass

    return _TRANSFORMER_MODEL, _SENTENCE_TRANSFORMER_LIB


def _normalize_text(text):
    """Normalise un texte: minuscules, sans accents (diacritiques), sans espaces superflus, préservant l'arabe."""
    if not text:
        return ""
    # NFKD sépare les lettres de base des diacritiques (accents français, tashkeel arabe)
    text_nfkd = unicodedata.normalize('NFKD', str(text))
    text_sans_accents = ''.join(c for c in text_nfkd if unicodedata.category(c) != 'Mn')
    return text_sans_accents.lower().strip()



def _classify_dci(dci):
    """Classifie une DCI ou terme dans l'une des familles pharmacologiques majeures."""
    if not dci:
        return None
    dci_upper = _normalize_text(dci).upper()

    # 1. Macrolides
    macrolides = ["AZITHROMYCINE", "CLARITHROMYCINE", "ERYTHROMYCINE", "ROXITHROMYCINE", "SPIRAMYCINE", "JOSAMYCINE", "MACROLID"]
    for macrolide in macrolides:
        if macrolide in dci_upper:
            return "macrolide"

    # 2. Pénicillines & Bêta-lactamines
    if any(p in dci_upper for p in ["CILLINE", "CILLIN", "PENICIL", "PENECIL", "AMOX", "AUGMENTIN", "CLAMOXYL", "AMPICIL", "OXACIL", "BETALACTAM", "BETA LACTAM"]):
        return "penicilline"

    # 3. Quinolones
    if any(q in dci_upper for q in ["FLOXACINE", "FLOXACIN", "QUINOLON"]):
        return "quinolone"

    # 4. Céphalosporines
    if any(c in dci_upper for c in ["CEPHALOSPORIN", "CPHALOSPORIN", "CEFTRIAXONE", "CEFIXIME", "CEFUROXIME", "CEF", "ROCEPHIN", "OROKEN"]):
        return "cephalosporine"

    # 5. Sulfamides
    if any(s in dci_upper for s in ["SULFAMID", "SULFONAMID", "COTRIMOXAZOL", "BACTRIM"]):
        return "sulfamide"
    words = dci_upper.split()
    for word in words:
        if word.startswith("SULFA") and "SULFATE" not in word and "SULFITE" not in word:
            return "sulfamide"

    # 6. Anti-inflammatoires (AINS), Aspirine & Paracétamol
    if any(a in dci_upper for a in ["ASPIRIN", "ACETYLSALICYL", "ASPEGIC", "KARDEGIC"]):
        return "aspirine"
    if any(i in dci_upper for i in ["IBUPROFEN", "KETOPROFEN", "DICLOFENAC", "VOLTAREN", "NAPROXEN", "APRANAX", "CELECOXIB", "ETORICOXIB", "MELOXICAM", "PIROXICAM", "INDOMETACIN", "FLURBIPROFEN", "TIAPROFEN", "PROFEN", "ADVIL", "NUROFEN", "AINS"]):
        return "ibuprofene"
    if any(p in dci_upper for p in ["PARACETAMOL", "ACETAMINOPHEN", "DOLIPRANE", "DAFALGAN", "EFFERALGAN"]):
        return "paracetamol"

    # 7. IEC (Inhibiteurs de l'Enzyme de Conversion)
    if any(p in dci_upper for p in ["RAMIPRIL", "CAPTOPRIL", "ENALAPRIL", "PERINDOPRIL", "LISINOPRIL", "BENAZEPRIL", "FOSINOPRIL", "QUINAPRIL", "ZOFENOPRIL", "TRANDOLAPRIL", "TRIATEC", "COVERSYL", "RENITEC", "PRIL"]):
        return "iec"

    # 8. ARA2 (Sartans)
    if any(s in dci_upper for s in ["LOSARTAN", "VALSARTAN", "CANDESARTAN", "IRBESARTAN", "TELMISARTAN", "OLMESARTAN", "EPROSARTAN", "AZILSARTAN", "COZAAR", "TAREG", "APROVEL", "MICARDIS", "SARTAN"]):
        return "ara2"

    # 9. Diurétiques épargneurs de potassium
    if any(d in dci_upper for d in ["SPIRONOLACTONE", "ALDACTONE", "EPLERENONE", "INSPRA", "AMILORIDE", "MODAMIDE", "TRIAMTERENE", "CANRENONE"]):
        return "diuretique_epargneur_potassium"

    # 10. AVK / Anticoagulants
    if any(v in dci_upper for v in ["WARFARIN", "COUMADIN", "FLUINDIONE", "PREVISCAN", "ACENOCOUMAROL", "SINTROM", "PHENINDIONE", "DABIGATRAN", "PRADAXA", "RIVAROXABAN", "XARELTO", "APIXABAN", "ELIQUIS", "EDOXABAN", "AVK", "ANTICOAGULANT"]):
        return "avk"

    # 11. Statines
    if any(st in dci_upper for st in ["ATORVASTATIN", "SIMVASTATIN", "ROSUVASTATIN", "PRAVASTATIN", "FLUVASTATIN", "PITAVASTATIN", "LOVASTATIN", "TAHOR", "LIPITOR", "CRESTOR", "ZOCOR", "ELISOR", "STATIN"]):
        return "statine"

    # 12. ISRS (Antidépresseurs sérotoninergiques)
    if any(isr in dci_upper for isr in ["FLUOXETIN", "PROZAC", "SERTRALIN", "ZOLOFT", "PAROXETIN", "DEROXAT", "CITALOPRAM", "ESCITALOPRAM", "SEROPLEX", "FLUVOXAMIN", "ISRS"]):
        return "isrs"

    # 13. Benzodiazépines
    if any(bzd in dci_upper for bzd in ["ALPRAZOLAM", "XANAX", "DIAZEPAM", "VALIUM", "LORAZEPAM", "TEMESTA", "BROMAZEPAM", "LEXOMIL", "PRAZEPAM", "LYSANXIA", "CLONAZEPAM", "RIVOTRIL", "OXAZEPAM", "SERESTA", "CLOBAZAM", "URBANYL", "CLORAZEPAT", "TRANXENE", "ZOLPIDEM", "STILNOX", "ZOPICLONE", "IMOVANE", "BENZODIAZEPIN", "BZD"]):
        return "benzodiazepine"

    # 14. Opioïdes / Morphiniques
    if any(op in dci_upper for op in ["TRAMADOL", "TOPALGIC", "IXPRIM", "ZALDIAR", "CODEIN", "CODOLIPRANE", "MORPHIN", "SKENAN", "MOSCONTIN", "FENTANYL", "DUROGESIC", "OXYCODON", "OXYCONTIN", "BUPRENORPHIN", "SUBUTEX", "METHADON", "TAPENTADOL", "OPIOID"]):
        return "opioide"

    # 15. Corticoïdes
    if any(co in dci_upper for co in ["PREDNISONE", "CORTANCYL", "PREDNISOLONE", "SOLUPRED", "METHYLPREDNISOLONE", "MEDROL", "DEXAMETHASONE", "BETAMETHASONE", "CELESTENE", "HYDROCORTISONE", "CORTICOID"]):
        return "corticoide"

    # 16. Méthotrexate, Lithium, Digoxine, Amiodarone
    if any(m in dci_upper for m in ["METHOTREXAT", "NOVATREX", "METOJECT"]):
        return "methotrexate"
    if any(l in dci_upper for l in ["LITHIUM", "TERALITHE"]):
        return "lithium"
    if any(dg in dci_upper for dg in ["DIGOXIN"]):
        return "digoxine"
    if any(am in dci_upper for am in ["AMIODARON", "CORDARONE"]):
        return "amiodarone"

    return None


def _get_bdpm_ontology():
    """Charge et structure l'ontologie médicamenteuse depuis FAMILLES_ALLERGIES, CLASSES_PHARMACOLOGIQUES et la BDPM (Thread-Safe Singleton)."""
    global _BDPM_CACHE
    if _BDPM_CACHE is not None:
        return _BDPM_CACHE

    with _BDPM_LOCK:
        if _BDPM_CACHE is not None:
            return _BDPM_CACHE

        med_to_family = {}

    # 1. Chargement des familles allergies et synonymes
    for famille, meds in FAMILLES_ALLERGIES.items():
        fam_norm = _normalize_text(famille)
        if fam_norm and len(fam_norm) >= 2:
            med_to_family[fam_norm] = fam_norm
            for m in meds:
                m_norm = _normalize_text(m)
                if m_norm and len(m_norm) >= 2:
                    med_to_family[m_norm] = fam_norm

    # 2. Chargement des classes pharmacologiques (interactions & doublons)
    for classe, meds in CLASSES_PHARMACOLOGIQUES.items():
        fam_target = 'ibuprofene' if classe == 'ains' else classe
        fam_norm = _normalize_text(fam_target)
        if fam_norm and len(fam_norm) >= 2:
            if fam_norm not in med_to_family:
                med_to_family[fam_norm] = fam_norm
            for m in meds:
                m_norm = _normalize_text(m)
                if m_norm and len(m_norm) >= 2:
                    if m_norm not in med_to_family:
                        med_to_family[m_norm] = fam_norm

    # 3. Chargement dynamique depuis les fichiers BDPM
    try:
        from odoo.tools.misc import file_path
        cis_file = file_path('cabinet_medical/data/CIS_bdpm.txt')
        compo_file = file_path('cabinet_medical/data/CIS_COMPO_bdpm.txt')
    except Exception:
        cis_file = get_module_resource('cabinet_medical', 'data', 'CIS_bdpm.txt')
        compo_file = get_module_resource('cabinet_medical', 'data', 'CIS_COMPO_bdpm.txt')

    if not cis_file or not compo_file:
        _BDPM_CACHE = MappingProxyType(med_to_family)
        return _BDPM_CACHE

    try:
        # Mapping CIS -> liste de DCI
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

        # Mapping Nom Commercial -> Famille via DCI
        with open(cis_file, 'r', encoding='latin-1') as f:
            for line in f:
                parts = line.strip('\n').split('\t')
                if len(parts) >= 2:
                    cis = parts[0].strip()
                    nom_commercial = parts[1].strip()

                    if cis in cis_to_dci:
                        for single_dci in cis_to_dci[cis]:
                            fam = _classify_dci(single_dci)
                            if fam:
                                fam_norm = _normalize_text(fam)
                                nom_norm = _normalize_text(nom_commercial)
                                if nom_norm and len(nom_norm) >= 2:
                                    med_to_family[nom_norm] = fam_norm

                                # Indexer également le premier mot (nom de marque seul, ex: "AUGMENTIN")
                                premier_mot = nom_norm.split()[0] if nom_norm.split() else ""
                                if premier_mot and len(premier_mot) >= 3 and premier_mot not in med_to_family:
                                    med_to_family[premier_mot] = fam_norm
                                # Indexer la DCI elle-même
                                dci_norm = _normalize_text(single_dci)
                                if dci_norm and len(dci_norm) >= 3 and dci_norm not in med_to_family:
                                    med_to_family[dci_norm] = fam_norm
                                break
    except Exception:
        pass

    _BDPM_CACHE = MappingProxyType(med_to_family)
    return _BDPM_CACHE


def _classify_medicament_or_famille(med_text):
    """
    Identifie la famille ou classe pharmacologique d'un médicament (nom commercial, DCI, formule avec dosage).
    Applique la normalisation NFKD, recherche dans l'ontologie BDPM, les classes pharmacologiques,
    les règles DCI et le fuzzy matching.
    """
    if not med_text:
        return None
    med_norm = _normalize_text(med_text)
    if not med_norm:
        return None

    # Nettoyage des formes galéniques / dosages superflus (ex: '500mg', '1g', 'cp', 'gelule')
    tokens = re.findall(r'[a-zA-Z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+', med_norm)

    med_to_family = _get_bdpm_ontology()

    # 1. Matching exact sur chaîne normalisée
    if med_norm in med_to_family:
        return med_to_family[med_norm]

    # 2. Matching par tokens (nom de spécialité ou DCI sans dosage)
    for t in tokens:
        if len(t) >= 3 and t in med_to_family:
            return med_to_family[t]

    # 3. Matching DCI / regex
    fam_dci = _classify_dci(med_norm)
    if fam_dci:
        return fam_dci
    for t in tokens:
        if len(t) >= 3:
            fam_dci_token = _classify_dci(t)
            if fam_dci_token:
                return fam_dci_token

    # 4. Préfixe / Suffixe sur dictionnaire
    for k, v in med_to_family.items():
        if len(k) >= 4 and len(med_norm) >= 4 and (med_norm.startswith(k) or k.startswith(med_norm)):
            return v

    # 5. Fuzzy matching (seuil >= 0.82)
    words_to_check = [med_norm] + [t for t in tokens if len(t) >= 4]
    best_ratio = 0.0
    best_fam = None
    for mot in words_to_check:
        len_m = len(mot)
        for k, v in med_to_family.items():
            if abs(len(k) - len_m) <= 2 and len(k) >= 4:
                ratio = difflib.SequenceMatcher(None, mot, k).ratio()
                if ratio > best_ratio and ratio >= 0.82:
                    best_ratio = ratio
                    best_fam = v

    return best_fam


def _format_family_name(family_key):
    """Formate le nom lisible d'une famille ou classe pharmacologique pour l'affichage."""
    mapping = {
        'iec': "IEC (Inhibiteur de l'Enzyme de Conversion)",
        'ara2': "ARA2 (Sartan)",
        'diuretique_epargneur_potassium': "Diurétique épargneur de potassium",
        'avk': "Anticoagulant (AVK / AOD)",
        'ains': "AINS (Anti-inflammatoire non stéroïdien)",
        'ibuprofene': "AINS (Anti-inflammatoire non stéroïdien)",
        'statine': "Statine (Hypolipémiant)",
        'macrolide': "Macrolide",
        'isrs': "Antidépresseur ISRS",
        'benzodiazepine': "Benzodiazépine",
        'opioide': "Opioïde / Morphinique",
        'corticoide': "Corticoïde",
        'penicilline': "Pénicilline",
        'cephalosporine': "Céphalosporine",
        'quinolone': "Fluoroquinolone",
        'sulfamide': "Sulfamide",
        'aspirine': "Aspirine / Salicylé",
        'paracetamol': "Paracétamol",
        'methotrexate': "Méthotrexate",
        'lithium': "Lithium",
        'digoxine': "Digoxine",
        'amiodarone': "Amiodarone",
    }
    return mapping.get(family_key, str(family_key).capitalize())


def _analyser_duree_traitement(date_presc, duree_str, ref_date=None):
    """
    Détermine si une prescription passée est toujours en cours d'action à la ref_date.
    Retourne (is_active, date_fin_estimee, libelle_duree).
    """
    ref = ref_date or date.today()
    if isinstance(ref, datetime):
        ref = ref.date()

    if not date_presc:
        return True, None, "Date inconnue"

    d_presc = date_presc
    if isinstance(d_presc, datetime):
        d_presc = d_presc.date()

    # Si la prescription est dans le futur ou aujourd'hui
    if d_presc >= ref:
        return True, d_presc, duree_str or "En cours"

    if not duree_str or not str(duree_str).strip():
        # Sans durée spécifiée, actif si prescrit il y a moins de 30 jours
        delta = (ref - d_presc).days
        return delta <= 30, d_presc + timedelta(days=30), "30 jours (par défaut)"

    duree_norm = _normalize_text(duree_str)

    # Mentions de traitement continu / chronique
    termes_chroniques = [
        "chronique", "long cours", "continu", "sans fin", "indefini",
        "fond", "habituel", "vie", "permanent", "renouvelable", "regulier"
    ]
    if any(tc in duree_norm for tc in termes_chroniques):
        return True, None, "Traitement chronique / continu"

    # Extraction numérique + unité
    match = re.search(r'(\d+)\s*(jour|j|semaine|sem|mois|m|an|annee)', duree_norm)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit in ('jour', 'j'):
            date_fin = d_presc + timedelta(days=val)
        elif unit in ('semaine', 'sem'):
            date_fin = d_presc + timedelta(weeks=val)
        elif unit in ('mois', 'm'):
            date_fin = d_presc + timedelta(days=int(val * 30.5))
        elif unit in ('an', 'annee'):
            date_fin = d_presc + timedelta(days=int(val * 365.25))
        else:
            date_fin = d_presc + timedelta(days=val)

        is_active = (date_fin >= ref)
        return is_active, date_fin, f"{val} {unit}(s)"

    # Fallback si un nombre simple sans unité (considéré en jours)
    num_match = re.search(r'\b(\d+)\b', duree_norm)
    if num_match:
        val = int(num_match.group(1))
        date_fin = d_presc + timedelta(days=val)
        return date_fin >= ref, date_fin, f"{val} jours"

    # Si durée non interprétable, actif si moins de 30 jours
    delta = (ref - d_presc).days
    return delta <= 30, d_presc + timedelta(days=30), str(duree_str)



# -------------------------------------------------------------------------
# MODÈLE PRESCRIPTION
# -------------------------------------------------------------------------

class Prescription(models.Model):
    _name = PRESCRIPTION_MODEL
    _description = 'Prescription/Ordonnance'
    _order = 'date_prescription desc'

    active = fields.Boolean(string='Actif', default=True, help='Désactiver pour archiver sans supprimer')

    consultation_id = fields.Many2one(CONSULTATION_MODEL, string='Consultation', required=True, ondelete='cascade')
    patient_id = fields.Many2one(related='consultation_id.patient_id', string='Patient', readonly=True)
    date_prescription = fields.Date(string='Date de prescription', required=True, default=fields.Date.today)

    # Lignes de prescription (médicaments)
    ordonnance_line_ids = fields.One2many(PRESCRIPTION_LINE_MODEL, 'prescription_id', string='Médicaments prescrits')
    medicaments_resume = fields.Char(
        string='Résumé des médicaments',
        compute='_compute_medicaments_resume',
        store=False
    )

    # Notes générales
    instructions = fields.Text(string='Instructions générales')
    instructions_summary = fields.Char(string='Instructions (résumé)', compute='_compute_instructions_summary', store=False)

    # Intelligence Artificielle
    ia_statut = fields.Selection([
        (IA_STATUT_NON_VERIFIE, 'Non Vérifié'),
        (IA_STATUT_SAFE, 'Aucun Risque Allergique'),
        (IA_STATUT_ALLERGY_RISK, 'Risque Allergique Détecté')
    ], string="Statut IA", default=IA_STATUT_NON_VERIFIE, copy=False)
    ia_message = fields.Text(string="Avis de l'IA", copy=False)
    ia_fingerprint = fields.Char(string="Empreinte IA", copy=False)
    ia_verified_by_user = fields.Boolean(string="Vérifié par l'utilisateur", default=False, copy=False)

    # État de l'ordonnance & Signature
    state = fields.Selection([
        (STATE_DRAFT, 'Brouillon'),
        (STATE_SIGNED, 'Signée'),
    ], string='Statut', default=STATE_DRAFT, required=True, copy=False)
    is_signed = fields.Boolean(string='Est Signée', default=False, copy=False)
    medecin_signataire_id = fields.Many2one('res.users', string='Médecin Signataire', readonly=True, copy=False)
    date_signature = fields.Datetime(string='Date et Heure de Signature', readonly=True, copy=False)
    signature_image = fields.Binary(
        string='Signature Apposée',
        readonly=True,
        copy=False,
        help="Copie immuable de l'image de signature apposée au moment exact de la signature."
    )

    # État de validation définitive & Marqueur IA
    is_validated = fields.Boolean(string="Validée", default=False, copy=False)
    is_ia_temporary_draft = fields.Boolean(
        string="Brouillon Temporaire IA",
        default=False,
        copy=False,
        help="Indique si l'ordonnance a été créée temporairement en base lors du clic 'Vérifier avec l'IA'"
    )
    create_date = fields.Datetime(string="Date de création", readonly=True, copy=False)

    # Contrôles de saisie
    @api.constrains('date_prescription')
    def _check_date_prescription(self):
        """Vérifier que la date de prescription n'est pas dans le futur"""
        for rec in self:
            if rec.date_prescription and rec.date_prescription > date.today():
                raise ValidationError("La date de prescription ne peut pas être dans le futur")

    @api.constrains('instructions')
    def _check_instructions(self):
        """Vérifier que les instructions ne sont pas trop courtes si renseignées"""
        for rec in self:
            if rec.instructions and len(rec.instructions.strip()) < 5:
                raise ValidationError("Les instructions générales doivent contenir au moins 5 caractères si elles sont renseignées")

    @api.constrains('ordonnance_line_ids', 'is_validated')
    def _check_ordonnance_lines(self):
        """Vérifier qu'il y a au moins un médicament prescrit lors de la validation"""
        for rec in self:
            lines = rec.ordonnance_line_ids
            active_lines = lines.filtered(lambda l: getattr(l, 'active', True)) if hasattr(lines, 'filtered') else [l for l in lines if getattr(l, 'active', True)]
            if rec.is_validated and not active_lines:
                raise ValidationError("Une ordonnance doit contenir au moins un médicament")

    @api.depends('ordonnance_line_ids.medicament')
    def _compute_medicaments_resume(self):
        for rec in self:
            noms = rec.ordonnance_line_ids.mapped('medicament')
            rec.medicaments_resume = ', '.join(filter(None, noms)) or '—'

    @api.depends('instructions')
    def _compute_instructions_summary(self):
        for rec in self:
            if rec.instructions:
                rec.instructions_summary = (rec.instructions[:100] + '…') if len(rec.instructions) > 100 else rec.instructions
            else:
                rec.instructions_summary = ''

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'ordonnance_line_ids' in fields_list and not defaults.get('ordonnance_line_ids'):
            defaults['ordonnance_line_ids'] = [(0, 0, {})]
        return defaults

    def name_get(self):
        result = []
        for prescription in self:
            date_str = prescription.date_prescription.strftime('%d/%m/%Y') if prescription.date_prescription else ''
            patient_name = prescription.patient_id.name if prescription.patient_id else ''
            name = f"Ordonnance - {patient_name} ({date_str})" if patient_name else f"Ordonnance du {date_str}"
            result.append((prescription.id, name))  # type: ignore
        return result

    def action_imprimer_ordonnance(self):
        """Imprimer l'ordonnance en PDF"""
        return self.env.ref('cabinet_medical.action_report_ordonnance').report_action(self)

    # -------------------------------------------------------------------------
    # EXTRACTION DU CONTEXTE DE VÉRIFICATION
    # -------------------------------------------------------------------------

    def _extract_verification_context(self):
        """Extrait le patient, la liste des médicaments prescrits et les allergies déclarées."""
        patient = self.patient_id or (self.consultation_id and self.consultation_id.patient_id)
        if not patient:
            patient_id_val = (
                self.env.context.get('default_patient_id')
                or self.env.context.get('patient_id')
                or self._context.get('default_patient_id')
                or self._context.get('patient_id')
            )
            if patient_id_val:
                patient = self.env['cabinet.patient'].browse(patient_id_val)

        if not patient and self.consultation_id:
            patient = self.consultation_id.patient_id

        if not patient:
            consultation_id_val = (
                self.env.context.get('default_consultation_id')
                or self.env.context.get('consultation_id')
                or self._context.get('default_consultation_id')
                or (self._context.get('active_model') == 'cabinet.consultation' and self._context.get('active_id'))
                or self._context.get('active_id')
            )
            if consultation_id_val:
                consultation = self.env['cabinet.consultation'].browse(consultation_id_val)
                if consultation.exists():
                    patient = consultation.patient_id

        medicaments_prescrits = [
            line.medicament.strip()
            for line in self.ordonnance_line_ids
            if line.medicament and line.medicament.strip() and getattr(line, 'active', True) is not False
        ]
        allergies_text = patient.allergies if patient else False
        return patient, medicaments_prescrits, allergies_text

    # -------------------------------------------------------------------------
    # NIVEAU 1 — VÉRIFICATION RAPIDE (ONTOLOGIE BDPM, FAMILLES, FUZZY MATCHING)
    # -------------------------------------------------------------------------

    def _verifier_niveau_1(self, medicaments_prescrits, allergies_text):
        """
        Niveau 1 — Vérification rapide :
        - Utilise la base de connaissances (FAMILLES_ALLERGIES + ontologie BDPM).
        - Applique la normalisation NFKD.
        - Exécute le matching exact, par famille pharmacologique, DCI et le fuzzy matching (SequenceMatcher >= 0.82).
        Retourne une liste de détections du Niveau 1.
        """
        alertes_n1 = []
        if not medicaments_prescrits or not allergies_text:
            return alertes_n1

        med_to_family = _get_bdpm_ontology()
        stop_words = {
            "allergie", "allergies", "allergique", "allergiques", "intolerance", "intolérance", "intolerant", "intolérant",
            "grave", "graves", "severe", "sévère", "severes", "sévères", "choc", "reaction", "réaction",
            "au", "aux", "a", "à", "la", "le", "les", "des", "du", "de", "d", "un", "une",
            "sur", "sous", "dans", "avec", "sans", "par", "pour", "en", "vers", "contre",
            "suite", "prise", "prise de", "apres", "après", "je", "suis", "il", "elle", "est",
            "patient", "patiente", "notion", "notion de", "antecedent", "antécédent", "connu", "connue",
            "et", "ou", "tres", "très",
            "حساسية", "من", "دواء", "شديدة", "المريض", "عنده"
        }

        allergies_list_brut = [a.strip() for a in re.split(r',| et | ou |\n| - |;|/|\.', allergies_text) if len(a.strip()) > 2]
        seuil_fuzzy = 0.82

        for med in medicaments_prescrits:
            med_norm = _normalize_text(med)
            med_mots = med_norm.split()
            famille_med = med_to_family.get(med_norm)
            if not famille_med:
                for mot in med_mots:
                    if len(mot) > 2 and mot in med_to_family:
                        famille_med = med_to_family[mot]
                        break
            if not famille_med:
                for k, v in med_to_family.items():
                    if len(k) >= 4 and len(med_norm) >= 4 and (med_norm.startswith(k) or k.startswith(med_norm)):
                        famille_med = v
                        break
            if not famille_med:
                famille_med = _classify_dci(med_norm)
            if not famille_med:
                for mot in med_mots:
                    famille_med = _classify_dci(mot)
                    if famille_med:
                        break
            if not famille_med:
                # Fuzzy matching optimisé contre l'ontologie BDPM (ex: 'augmantin' -> 'augmentin', 'dolpirane' -> 'doliprane')
                best_fuzzy_score = 0.0
                words_to_check = [med_norm] + [m for m in med_mots if len(m) >= 4]
                for mot in words_to_check:
                    len_m = len(mot)
                    for k, v in med_to_family.items():
                        if abs(len(k) - len_m) <= 2 and len(k) >= 4:
                            ratio = difflib.SequenceMatcher(None, mot, k).ratio()
                            if ratio > best_fuzzy_score and ratio >= seuil_fuzzy:
                                best_fuzzy_score = ratio
                                famille_med = v

            for phrase_allergie in allergies_list_brut:
                mots_al = phrase_allergie.split()
                mots_al_utiles = [m for m in mots_al if _normalize_text(m) not in stop_words and len(m) > 2]
                texte_al_utile = " ".join(mots_al_utiles) if mots_al_utiles else phrase_allergie

                allergie_norm = _normalize_text(texte_al_utile)
                allergie_mots = allergie_norm.split()

                famille_allergie = med_to_family.get(allergie_norm)
                if not famille_allergie:
                    for mot in allergie_mots:
                        famille_allergie = med_to_family.get(mot)
                        if famille_allergie:
                            break
                if not famille_allergie:
                    famille_allergie = _classify_dci(allergie_norm)
                if not famille_allergie:
                    for mot in allergie_mots:
                        famille_allergie = _classify_dci(mot)
                        if famille_allergie:
                            break


                score_max = 0.0
                raison = ""
                type_detection = "fuzzy"

                # A. Règles strictes / Exact match
                for mot_med in med_mots:
                    for mot_al in allergie_mots:
                        if mot_med == mot_al or (len(mot_al) > 3 and mot_al in mot_med) or (len(mot_med) > 3 and mot_med in mot_al):
                            score_max = 1.0
                            type_detection = "exact"
                            raison = "Correspondance exacte détectée"
                            break
                    if score_max >= 1.0:
                        break

                # B. Règles d'ontologie par famille pharmacologique
                if score_max < 1.0 and famille_med:
                    synonymes_famille = FAMILLES_ALLERGIES.get(famille_med, [])
                    if famille_allergie and famille_med == famille_allergie:
                        score_max = 1.0
                        type_detection = "famille"
                        raison = f"Alerte Famille : {famille_med.capitalize()}"
                    elif _normalize_text(famille_med) in allergie_norm:
                        score_max = 1.0
                        type_detection = "famille"
                        raison = f"Appartient à la famille des {famille_med.capitalize()}s"
                    elif any(_normalize_text(syn) in allergie_norm for syn in synonymes_famille if len(_normalize_text(syn)) >= 3):
                        score_max = 1.0
                        type_detection = "famille"
                        raison = f"Correspondance avec un dérivé de la famille {famille_med.capitalize()}"
                    elif famille_med in FAMILLES_ANTIBIOTIQUES and any(_normalize_text(t) in allergie_norm for t in TERMES_GENERIQUE_ANTIBIO):
                        score_max = 1.0
                        type_detection = "famille"
                        raison = f"Alerte Classe Générique : Antibiotique (Famille : {famille_med.capitalize()})"


                # C. Correspondance Floue (difflib.SequenceMatcher)
                if score_max < 1.0:
                    for mot_med in med_mots:
                        for mot_al in allergie_mots:
                            ratio_med = difflib.SequenceMatcher(None, mot_med, mot_al).ratio()
                            if ratio_med > score_max:
                                score_max = ratio_med
                                type_detection = "fuzzy"
                                raison = "Correction orthographique automatique (Fuzzy matching)"

                    if famille_med:
                        for mot_al in allergie_mots:
                            ratio_fam = difflib.SequenceMatcher(None, famille_med, mot_al).ratio()
                            if ratio_fam > score_max:
                                score_max = ratio_fam
                                type_detection = "fuzzy"
                                raison = f"Correction orthographique sur la famille {famille_med.capitalize()}"

                if score_max >= seuil_fuzzy:
                    alertes_n1.append({
                        KEY_MEDICAMENT: med,
                        'allergie': phrase_allergie,
                        KEY_SCORE: score_max,
                        KEY_TYPE: type_detection,
                        KEY_RAISON: raison,
                        KEY_FAMILLE: famille_med,
                    })

        return alertes_n1

    # -------------------------------------------------------------------------
    # NIVEAU 2 — ANALYSE APPROFONDIE (MODÈLE TRANSFORMER NLP SÉMANTIQUE)
    # -------------------------------------------------------------------------

    def _verifier_niveau_2(self, medicaments_prescrits, allergies_text):
        """
        Niveau 2 — Analyse approfondie :
        - Exécute le modèle Transformer NLP SentenceTransformer ('paraphrase-multilingual-MiniLM-L12-v2').
        - Calcule les similarités cosinus d'embeddings sémantiques.
        - Détecte les correspondances complexes ou sémantiques (seuil >= 0.70).
        Retourne une liste de détections du Niveau 2.
        """
        alertes_n2 = []
        if not medicaments_prescrits or not allergies_text:
            return alertes_n2

        allergies_list_brut = [a.strip() for a in re.split(r',| et | ou |\n| - ', allergies_text) if len(a.strip()) > 2]
        if not allergies_list_brut:
            return alertes_n2

        try:
            model, libs = _get_transformer_model()
            if model is not None and libs is not None:
                util, torch = libs
                with torch.no_grad():
                    med_embeddings = model.encode(medicaments_prescrits, convert_to_tensor=True)
                    al_embeddings = model.encode(allergies_list_brut, convert_to_tensor=True)
                    cosine_scores = util.cos_sim(med_embeddings, al_embeddings)

                seuil_transformer = 0.70
                for i, med in enumerate(medicaments_prescrits):
                    for j, allergie in enumerate(allergies_list_brut):
                        score = cosine_scores[i][j].item()
                        if score >= seuil_transformer:
                            alertes_n2.append({
                                KEY_MEDICAMENT: med,
                                'allergie': allergie,
                                KEY_SCORE: score,
                                KEY_TYPE: 'nlp_semantique',
                                KEY_RAISON: "Similarité Sémantique IA Multilingue (Transformer NLP)",
                            })
        except Exception:
            pass

        return alertes_n2

    # -------------------------------------------------------------------------
    # GESTION DES TRAITEMENTS ACTIFS & HISTORIQUE DU PATIENT
    # -------------------------------------------------------------------------

    def _extraire_traitements_actifs(self, patient=None, reference_date=None):
        """
        Extrait la liste consolidée des traitements actifs du patient :
        1. Traitements chroniques déclarés sur le dossier patient.
        2. Prescriptions antérieures dont la durée de traitement n'est pas encore écoulée.
        """
        pat = patient or self.patient_id or (self.consultation_id and self.consultation_id.patient_id)
        if not pat:
            return []

        ref_date = reference_date or self.date_prescription or date.today()
        traitements = []

        # 1. Traitements chroniques (champ Text libre sur patient)
        tc_text = getattr(pat, 'traitements_chroniques', False) or ""
        if tc_text and str(tc_text).strip():
            lignes = [l.strip() for l in re.split(r'[\n;,/]+| - ', str(tc_text)) if len(l.strip()) >= 2]
            for l in lignes:
                traitements.append({
                    KEY_MEDICAMENT: l,
                    KEY_SOURCE: 'Traitement chronique (Dossier patient)',
                    KEY_SOURCE_TYPE: 'chronique',
                    KEY_DATE_PRESCRIPTION: False,
                    KEY_DUREE: 'Chronique',
                    KEY_IS_ACTIVE: True,
                })

        # 2. Prescriptions antérieures en base / relationnelles
        current_id = False
        try:
            val_id = getattr(self, 'id', False)
            if isinstance(val_id, int) and val_id > 0:
                current_id = val_id
        except Exception:
            current_id = False

        prescriptions = []
        if pat and hasattr(pat, 'consultation_ids') and pat.consultation_ids:
            try:
                for c in pat.consultation_ids:
                    p_ids = getattr(c, 'prescription_ids', [])
                    if p_ids and hasattr(p_ids, '__iter__'):
                        for p in p_ids:
                            if getattr(p, 'active', True) and getattr(p, 'id', None) != current_id:
                                prescriptions.append(p)
            except Exception:
                pass

        if not prescriptions and hasattr(self, 'env') and self.env:
            try:
                presc_domain = [('patient_id', '=', pat.id), ('active', '=', True)]
                if current_id:
                    presc_domain.append(('id', '!=', current_id))
                res = self.env[PRESCRIPTION_MODEL].search(presc_domain)
                if res and hasattr(res, '__iter__') and type(res).__name__ not in ('MagicMock', 'Mock'):
                    prescriptions = res
            except Exception:
                pass

        if prescriptions:
            for p in prescriptions:
                d_presc = getattr(p, 'date_prescription', False)
                lines = getattr(p, 'ordonnance_line_ids', [])
                if lines and hasattr(lines, '__iter__'):
                    for line in lines:
                        if getattr(line, 'active', True) is False:
                            continue
                        med_name = getattr(line, 'medicament', '')
                        if not med_name or not str(med_name).strip():
                            continue
                        duree_val = getattr(line, 'duree', '')
                        is_active, d_fin, libelle_duree = _analyser_duree_traitement(d_presc, duree_val, ref_date)
                        if is_active:
                            date_str = d_presc.strftime(DATE_FORMAT) if hasattr(d_presc, 'strftime') else str(d_presc)
                            traitements.append({
                                KEY_MEDICAMENT: med_name,
                                KEY_SOURCE: f"Ordonnance du {date_str} (durée: {duree_val or 'N/C'})",
                                KEY_SOURCE_TYPE: 'prescription_recente',
                                KEY_DATE_PRESCRIPTION: d_presc,
                                KEY_DUREE: duree_val,
                                KEY_IS_ACTIVE: True,
                            })

        return traitements

    # -------------------------------------------------------------------------
    # VÉRIFICATION DES INTERACTIONS MÉDICAMENTEUSES & DOUBLONS THÉRAPEUTIQUES
    # -------------------------------------------------------------------------

    def _verifier_interactions_medicamenteuses(self, medicaments_prescrits, patient=None, reference_date=None, context_traitements=None):
        """
        Vérifie :
        1. Les interactions médicamenteuses dangereuses (Type A) ET doublons thérapeutiques (Type B)
           DANS la même ordonnance (entre tous les médicaments nouvellement prescrits).
        2. Les interactions médicamenteuses dangereuses (Type A) ET doublons thérapeutiques (Type B)
           ENTRE les médicaments prescrits et les traitements actifs du patient (chroniques + ordonnances récentes non expirées).
        """
        alertes = []
        if not medicaments_prescrits:
            return alertes

        # 1. Classification de tous les médicaments de la nouvelle ordonnance
        meds_prescrits_classes = []
        for med in medicaments_prescrits:
            if not med or not str(med).strip():
                continue
            fam = _classify_medicament_or_famille(med)
            meds_prescrits_classes.append({
                'medicament': str(med).strip(),
                'famille': fam
            })

        # 2. Récupération et classification des traitements actifs existants
        if context_traitements is not None:
            traitements_actifs = context_traitements
        else:
            traitements_actifs = self._extraire_traitements_actifs(patient, reference_date)

        traitements_classes = []
        for t in traitements_actifs:
            m_name = t.get('medicament', '')
            if not m_name or not str(m_name).strip():
                continue
            fam = _classify_medicament_or_famille(m_name)
            traitements_classes.append({
                'medicament': str(m_name).strip(),
                'famille': fam,
                'source': t.get('source', 'Traitement actif'),
                'source_type': t.get('source_type', 'inconnu')
            })

        # Index des interactions connues (clé symétrique ordonnée)
        interactions_map = {}
        for inter in INTERACTIONS_MEDICAMENTEUSES:
            f_a = inter[KEY_FAMILLE_A]
            f_b = inter[KEY_FAMILLE_B]
            key = tuple(sorted([f_a, f_b]))
            interactions_map[key] = inter

        vus = set()

        # ---------------------------------------------------------------------
        # A. VÉRIFICATION INTRA-ORDONNANCE (ENTRE MÉDICAMENTS DE LA MÊME PRESCRIPTION)
        # ---------------------------------------------------------------------
        n = len(meds_prescrits_classes)
        for i in range(n):
            for j in range(i + 1, n):
                m1 = meds_prescrits_classes[i]
                m2 = meds_prescrits_classes[j]
                fam1 = m1[KEY_FAMILLE]
                fam2 = m2[KEY_FAMILLE]

                if not fam1 or not fam2:
                    continue

                pair_key = tuple(sorted([_normalize_text(m1[KEY_MEDICAMENT]), _normalize_text(m2[KEY_MEDICAMENT])]))

                # 1. Doublon thérapeutique intra-ordonnance (même famille, ex: 2 AINS ou 2 IEC)
                is_same_family = (fam1 == fam2) or (fam1 in (FAMILLE_AINS, FAMILLE_IBUPROFENE) and fam2 in (FAMILLE_AINS, FAMILLE_IBUPROFENE))
                if is_same_family:
                    dedup_key = (TYPE_DOUBLON, pair_key)
                    if dedup_key not in vus:
                        vus.add(dedup_key)
                        fam_nom = _format_family_name(fam1)
                        alertes.append({
                            KEY_TYPE: TYPE_DOUBLON,
                            KEY_TYPE_LABEL: 'Doublon Thérapeutique',
                            KEY_GRAVITE: GRAVITE_MODEREE,
                            KEY_MEDICAMENT_A: m1[KEY_MEDICAMENT],
                            KEY_MEDICAMENT_B: m2[KEY_MEDICAMENT],
                            KEY_FAMILLE_A: fam1,
                            KEY_FAMILLE_B: fam2,
                            KEY_TITRE: f"Doublon thérapeutique : {fam_nom}",
                            KEY_RAISON: f"Prescription simultanée de deux médicaments de la même famille pharmacologique ('{m1[KEY_MEDICAMENT]}' et '{m2[KEY_MEDICAMENT]}'). Risque de surdosage ou d'effets indésirables cumulatifs sans bénéfice thérapeutique démontré.",
                            KEY_CONTEXTE: "Même ordonnance",
                        })

                # 2. Interaction dangereuse intra-ordonnance
                inter_key = tuple(sorted([fam1, fam2]))
                if inter_key not in interactions_map:
                    f1_equiv = FAMILLE_AINS if fam1 == FAMILLE_IBUPROFENE else fam1
                    f2_equiv = FAMILLE_AINS if fam2 == FAMILLE_IBUPROFENE else fam2
                    inter_key = tuple(sorted([f1_equiv, f2_equiv]))

                if inter_key in interactions_map:
                    inter = interactions_map[inter_key]
                    dedup_key = (TYPE_INTERACTION, pair_key)
                    if dedup_key not in vus:
                        vus.add(dedup_key)
                        alertes.append({
                            KEY_TYPE: TYPE_INTERACTION,
                            KEY_TYPE_LABEL: 'Interaction Dangereuse',
                            KEY_GRAVITE: inter[KEY_GRAVITE],
                            KEY_MEDICAMENT_A: m1[KEY_MEDICAMENT],
                            KEY_MEDICAMENT_B: m2[KEY_MEDICAMENT],
                            KEY_FAMILLE_A: fam1,
                            KEY_FAMILLE_B: fam2,
                            KEY_TITRE: inter[KEY_TITRE],
                            KEY_RAISON: inter[KEY_RAISON],
                            KEY_CONTEXTE: "Même ordonnance",
                        })

        # ---------------------------------------------------------------------
        # B. VÉRIFICATION AVEC L'HISTORIQUE & TRAITEMENTS ACTIFS DU PATIENT
        # ---------------------------------------------------------------------
        for m in meds_prescrits_classes:
            fam_presc = m[KEY_FAMILLE]
            if not fam_presc:
                continue

            for t in traitements_classes:
                fam_trait = t[KEY_FAMILLE]
                if not fam_trait:
                    continue

                pair_key = tuple(sorted([_normalize_text(m[KEY_MEDICAMENT]), _normalize_text(t[KEY_MEDICAMENT])]))

                # 1. Doublon thérapeutique avec traitement actif
                is_same_family = (fam_presc == fam_trait) or (fam_presc in (FAMILLE_AINS, FAMILLE_IBUPROFENE) and fam_trait in (FAMILLE_AINS, FAMILLE_IBUPROFENE))
                if is_same_family:
                    dedup_key = (TYPE_DOUBLON, pair_key)
                    if dedup_key not in vus:
                        vus.add(dedup_key)
                        fam_nom = _format_family_name(fam_presc)
                        alertes.append({
                            KEY_TYPE: TYPE_DOUBLON,
                            KEY_TYPE_LABEL: 'Doublon Thérapeutique',
                            KEY_GRAVITE: GRAVITE_MODEREE,
                            KEY_MEDICAMENT_A: m[KEY_MEDICAMENT],
                            KEY_MEDICAMENT_B: t[KEY_MEDICAMENT],
                            KEY_FAMILLE_A: fam_presc,
                            KEY_FAMILLE_B: fam_trait,
                            KEY_TITRE: f"Doublon thérapeutique : {fam_nom}",
                            KEY_RAISON: f"Le patient prend déjà '{t[KEY_MEDICAMENT]}' ({t[KEY_SOURCE]}) appartenant à la même famille des {fam_nom}. La nouvelle prescription de '{m[KEY_MEDICAMENT]}' entraîne un doublon thérapeutique redondant.",
                            KEY_CONTEXTE: t[KEY_SOURCE],
                        })

                # 2. Interaction dangereuse avec traitement actif
                inter_key = tuple(sorted([fam_presc, fam_trait]))
                if inter_key not in interactions_map:
                    f1_equiv = FAMILLE_AINS if fam_presc == FAMILLE_IBUPROFENE else fam_presc
                    f2_equiv = FAMILLE_AINS if fam_trait == FAMILLE_IBUPROFENE else fam_trait
                    inter_key = tuple(sorted([f1_equiv, f2_equiv]))

                if inter_key in interactions_map:
                    inter = interactions_map[inter_key]
                    dedup_key = (TYPE_INTERACTION, pair_key)
                    if dedup_key not in vus:
                        vus.add(dedup_key)
                        alertes.append({
                            KEY_TYPE: TYPE_INTERACTION,
                            KEY_TYPE_LABEL: 'Interaction Dangereuse',
                            KEY_GRAVITE: inter[KEY_GRAVITE],
                            KEY_MEDICAMENT_A: m[KEY_MEDICAMENT],
                            KEY_MEDICAMENT_B: t[KEY_MEDICAMENT],
                            KEY_FAMILLE_A: fam_presc,
                            KEY_FAMILLE_B: fam_trait,
                            KEY_TITRE: inter[KEY_TITRE],
                            KEY_RAISON: inter[KEY_RAISON],
                            KEY_CONTEXTE: t[KEY_SOURCE],
                        })

        gravite_ordre = {GRAVITE_MAJEURE: 0, GRAVITE_MODEREE: 1, 'mineure': 2}
        alertes.sort(key=lambda x: gravite_ordre.get(x.get(KEY_GRAVITE, GRAVITE_MODEREE), 9))
        return alertes

    # -------------------------------------------------------------------------
    # FUSION DES RÉSULTATS & DÉDUPLICATION INTELLIGENTE
    # -------------------------------------------------------------------------

    def _fusionner_resultats_ia(self, alertes_n1, alertes_n2, medicaments_prescrits, allergies_text, alertes_interactions=None, traitements_actifs=None):
        """
        Fusionne les résultats des vérifications Allergies (N1 + N2) et Interactions médicamenteuses / Doublons :
        - Évite les doublons.
        - Consolide les informations et formule un compte-rendu clair et distinct.
        - Détermine le statut final ('safe' ou 'allergy_risk') et formule les notifications.
        """
        if not medicaments_prescrits:
            return 'non_verifie', "Veuillez d'abord ajouter au moins un médicament.", {
                'title': "IA : Prescription vide",
                KEY_MESSAGE: "Veuillez ajouter au moins un médicament à l'ordonnance.",
                KEY_TYPE: LEVEL_WARNING
            }

        # Dictionnaire pour consolider les alertes allergies par clé normalisée (med, allergie)
        dedup_map_allergies = {}
        for a in (alertes_n1 or []):
            key = (_normalize_text(a[KEY_MEDICAMENT]), _normalize_text(a['allergie']))
            dedup_map_allergies[key] = {
                KEY_MEDICAMENT: a[KEY_MEDICAMENT],
                'allergie': a['allergie'],
                'n1': a,
                'n2': None,
            }

        for a in (alertes_n2 or []):
            key = (_normalize_text(a[KEY_MEDICAMENT]), _normalize_text(a['allergie']))
            if key in dedup_map_allergies:
                dedup_map_allergies[key]['n2'] = a
            else:
                dedup_map_allergies[key] = {
                    KEY_MEDICAMENT: a[KEY_MEDICAMENT],
                    'allergie': a['allergie'],
                    'n1': None,
                    'n2': a,
                }

        interactions = alertes_interactions or []
        has_allergy_risk = bool(dedup_map_allergies)
        has_interaction_risk = bool(interactions)

        # Si aucun risque allergique et aucune interaction
        if not has_allergy_risk and not has_interaction_risk:
            msg = (
                "✅ Aucun risque allergique détecté.\n"
                "• Niveau 1 (Ontologie BDPM & Fuzzy Matching) : Validé (0 risque)\n"
                "• Niveau 2 (Analyse Sémantique Transformer NLP) : Validé (0 risque)"
            )
            return IA_STATUT_SAFE, msg, {
                KEY_TITLE: "IA Locale : Sécurisé",
                KEY_MESSAGE: "Aucun risque allergique détecté (Vérification multi-niveaux validée).",
                KEY_TYPE: LEVEL_SUCCESS
            }

        sections = []
        noms_meds_risques = set()

        # Section 1 : Risques Allergiques
        if has_allergy_risk:
            lignes_al = []
            for item in dedup_map_allergies.values():
                med = item[KEY_MEDICAMENT]
                allergie = item['allergie']
                noms_meds_risques.add(med)

                if item['n1'] and item['n2']:
                    score_n1 = int(item['n1'][KEY_SCORE] * 100)
                    score_n2 = int(item['n2'][KEY_SCORE] * 100)
                    detail_n1 = item['n1'][KEY_RAISON]
                    lignes_al.append(
                        f"⚠️ [Niveau 1 & 2 Confirmé] '{med}' vs allergie '{allergie}'\n"
                        f"   - Niveau 1 (Ontologie/Fuzzy) : {score_n1}% ({detail_n1})\n"
                        f"   - Niveau 2 (NLP Sémantique)  : {score_n2}% (Similarité cosinus Transformer)"
                    )
                elif item['n1']:
                    score_n1 = int(item['n1'][KEY_SCORE] * 100)
                    detail_n1 = item['n1'][KEY_RAISON]
                    lignes_al.append(
                        f"⚠️ [Niveau 1 — Ontologie/Règle] '{med}' vs allergie '{allergie}'\n"
                        f"   - Confiance de la correspondance : {score_n1}% ({detail_n1})"
                    )
                else:
                    score_n2 = int(item['n2'][KEY_SCORE] * 100)
                    lignes_al.append(
                        f"⚠️ [Niveau 2 — Analyse Sémantique NLP] '{med}' vs allergie '{allergie}'\n"
                        f"   - Fiabilité Sémantique : {score_n2}% (Modèle Transformer multilingue)"
                    )

            texte_al = "\n\n".join(lignes_al)
            sections.append(
                "🚨 ALERTE ALLERGIE (Vérification multi-niveaux) :\n\n"
                f"{texte_al}\n\n"
                "─────────────\n"
                f"• Niveau 1 (Vérification rapide BDPM & Fuzzy) : {len(alertes_n1 or [])} détection(s)\n"
                f"• Niveau 2 (Analyse approfondie Transformer NLP) : {len(alertes_n2 or [])} détection(s)"
            )

        # Section 2 : Interactions Médicamenteuses & Doublons
        if has_interaction_risk:
            lignes_inter = []
            for inter in interactions:
                m_a = inter[KEY_MEDICAMENT_A]
                m_b = inter[KEY_MEDICAMENT_B]
                noms_meds_risques.add(m_a)
                noms_meds_risques.add(m_b)
                gravite = inter.get(KEY_GRAVITE, GRAVITE_MODEREE).upper()
                titre = inter.get(KEY_TITRE, '')
                raison = inter.get(KEY_RAISON, '')
                contexte = inter.get(KEY_CONTEXTE, '')
                t_label = inter.get(KEY_TYPE_LABEL, 'Interaction')

                if inter[KEY_TYPE] == TYPE_INTERACTION:
                    icone = "⛔" if gravite == "MAJEURE" else "⚠️"
                    lignes_inter.append(
                        f"{icone} [{t_label} - Gravité {gravite}] {titre}\n"
                        f"   • Combinaison : '{m_a}' ↔ '{m_b}' ({contexte})\n"
                        f"   • Risque clinique : {raison}"
                    )
                else:
                    # Doublon thérapeutique (Type B)
                    lignes_inter.append(
                        f"🔄 [{t_label}] {titre}\n"
                        f"   • Médicaments concernés : '{m_a}' ↔ '{m_b}' ({contexte})\n"
                        f"   • Analyse : {raison}"
                    )

            texte_inter = "\n\n".join(lignes_inter)
            sections.append(
                "⚠️ ALERTES PHARMACOLOGIQUES (Interactions & Doublons) :\n\n"
                f"{texte_inter}"
            )

        message_final = "\n\n═════════════════════════════════════\n\n".join(sections)

        meds_str = ", ".join(sorted(noms_meds_risques))
        if has_allergy_risk and has_interaction_risk:
            notif_title = "⚠️ Alertes Allergies & Interactions détectées"
            notif_msg = f"Risques allergiques et interactions détectés pour : {meds_str}."
        elif has_allergy_risk:
            notif_title = "⚠️ Alerte allergique détectée"
            notif_msg = f"Risque allergique détecté pour : {meds_str}."
        else:
            notif_title = "⚠️ Interaction / Doublon médicamenteux"
            notif_msg = f"Interaction ou doublon détecté pour : {meds_str}."

        return IA_STATUT_ALLERGY_RISK, message_final, {
            KEY_TITLE: notif_title,
            KEY_MESSAGE: notif_msg,
            KEY_TYPE: LEVEL_DANGER
        }

    def _compute_ia_fingerprint(self, medicaments=None, allergies=None, patient_id=None, traitements=None):
        """Calcule une empreinte MD5 déterministe basée sur le patient, les allergies, les traitements chroniques et les médicaments."""
        patient, meds_ctx, al_ctx = self._extract_verification_context()
        meds = medicaments if medicaments is not None else meds_ctx
        allergies_val = allergies if allergies is not None else al_ctx

        p_id = patient_id if patient_id is not None else (patient.id if patient else '')
        pat_id = str(p_id or '')
        meds_key = "|".join(sorted(_normalize_text(m) for m in (meds or [])))
        al_key = _normalize_text(allergies_val or '')

        tc_val = None
        if isinstance(traitements, str):
            tc_val = traitements
        elif patient and hasattr(patient, 'traitements_chroniques'):
            raw_tc = getattr(patient, 'traitements_chroniques', '')
            if isinstance(raw_tc, str):
                tc_val = raw_tc
        tc_key = _normalize_text(tc_val or '')

        raw = f"{pat_id}::{meds_key}::{al_key}::{tc_key}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _calculate_ia_status(self):
        """Méthode de calcul unifiée séquentielle (Niveau 1 -> Niveau 2 -> Interactions -> Fusion)."""
        patient, medicaments, allergies = self._extract_verification_context()
        alertes_n1 = self._verifier_niveau_1(medicaments, allergies)
        alertes_n2 = self._verifier_niveau_2(medicaments, allergies)
        alertes_interactions = self._verifier_interactions_medicamenteuses(medicaments, patient=patient)
        traitements_actifs = self._extraire_traitements_actifs(patient=patient)
        statut, message, notif = self._fusionner_resultats_ia(
            alertes_n1, alertes_n2, medicaments, allergies,
            alertes_interactions=alertes_interactions,
            traitements_actifs=traitements_actifs
        )
        return statut, message, notif

    # -------------------------------------------------------------------------
    # RÉINITIALISATION EN TEMPS RÉEL (ONCHANGE - AUCUN APPEL IA AUTOMATIQUE)
    # -------------------------------------------------------------------------

    @api.onchange('ordonnance_line_ids', 'patient_id', 'consultation_id')
    def _onchange_ordonnance_lines_ia(self):
        """
        Réinitialise l'état IA lors de toute modification des lignes ou du patient.
        RÈGLE : Aucun appel IA n'est déclenché ici (l'IA ne tourne que sur clic bouton ou sauvegarde).
        """
        for record in self:
            record.ia_statut = 'non_verifie'
            record.ia_message = False
            record.ia_fingerprint = False
            record.ia_verified_by_user = False

    # -------------------------------------------------------------------------
    # ANALYSE IA 100% EN MÉMOIRE (POUR NOUVELLES ORDONNANCES SANS CREATE EN BASE)
    # -------------------------------------------------------------------------

    @api.model
    def verify_ia_in_memory(self, vals):
        """
        Exécute l'analyse IA 100% en mémoire pour un formulaire en cours d'édition,
        SANS créer ni sauvegarder d'enregistrement en base de données PostgreSQL.
        """
        patient_id = vals.get('patient_id')
        if isinstance(patient_id, (list, tuple)) and patient_id:
            patient_id = patient_id[0]
        patient = self.env['cabinet.patient'].browse(patient_id) if patient_id else False
        allergies_val = getattr(patient, 'allergies', False) if patient else False
        allergies_text = vals.get('allergies') or (allergies_val if isinstance(allergies_val, str) else False)

        traitements_chroniques_val = vals.get('traitements_chroniques') or (getattr(patient, 'traitements_chroniques', False) if patient else False)

        raw_lines = vals.get('ordonnance_line_ids') or []
        medicaments = []
        for cmd in raw_lines:
            if isinstance(cmd, (list, tuple)) and len(cmd) >= 3 and isinstance(cmd[2], dict):
                med = cmd[2].get('medicament')
                if med and str(med).strip() and cmd[2].get('active', True) is not False:
                    medicaments.append(str(med).strip())
            elif isinstance(cmd, dict):
                med = cmd.get('medicament')
                if med and str(med).strip() and cmd.get('active', True) is not False:
                    medicaments.append(str(med).strip())
            elif isinstance(cmd, (list, tuple)) and len(cmd) >= 2 and cmd[0] == 4:
                line_rec = self.env[PRESCRIPTION_LINE_MODEL].browse(cmd[1])
                if line_rec.exists() and line_rec.medicament:
                    medicaments.append(line_rec.medicament.strip())

        if not medicaments:
            return {
                FIELD_IA_STATUT: IA_STATUT_NON_VERIFIE,
                FIELD_IA_MESSAGE: False,
                FIELD_IA_FINGERPRINT: False,
                'notification': {
                    KEY_TITLE: "Vérification IA",
                    KEY_MESSAGE: "Aucun médicament n'a été ajouté à cette ordonnance.",
                    KEY_TYPE: LEVEL_INFO,
                    'sticky': False,
                }
            }

        alertes_n1 = self._verifier_niveau_1(medicaments, allergies_text)
        alertes_n2 = self._verifier_niveau_2(medicaments, allergies_text)

        traitements_actifs = self._extraire_traitements_actifs(patient=patient)
        if traitements_chroniques_val and not any(t[KEY_SOURCE_TYPE] == 'chronique' for t in traitements_actifs):
            for l in [x.strip() for x in re.split(r'[\n;,/]+| - ', str(traitements_chroniques_val)) if len(x.strip()) >= 2]:
                traitements_actifs.append({
                    KEY_MEDICAMENT: l,
                    KEY_SOURCE: 'Traitement chronique (Dossier patient)',
                    KEY_SOURCE_TYPE: 'chronique',
                    KEY_DATE_PRESCRIPTION: False,
                    KEY_DUREE: 'Chronique',
                    KEY_IS_ACTIVE: True
                })

        alertes_interactions = self._verifier_interactions_medicamenteuses(medicaments, patient=patient, context_traitements=traitements_actifs)
        statut, message, notif = self._fusionner_resultats_ia(
            alertes_n1, alertes_n2, medicaments, allergies_text,
            alertes_interactions=alertes_interactions,
            traitements_actifs=traitements_actifs
        )
        fp = self._compute_ia_fingerprint(medicaments, allergies_text, patient_id=patient_id, traitements=traitements_chroniques_val)

        return {
            FIELD_IA_STATUT: statut,
            FIELD_IA_MESSAGE: message,
            FIELD_IA_FINGERPRINT: fp,
            'notification': {
                KEY_TITLE: notif[KEY_TITLE],
                KEY_MESSAGE: notif[KEY_MESSAGE],
                KEY_TYPE: notif[KEY_TYPE],
                'sticky': notif[KEY_TYPE] == LEVEL_DANGER,
            }
        }

    # -------------------------------------------------------------------------
    # ACTION BOUTON : « 🤖 VÉRIFIER AVEC L'IA » (SUR ENREGISTREMENT EXISTANT)
    # -------------------------------------------------------------------------

    def action_verifier_ia(self) -> bool:
        """
        Point d'entrée volontaire du médecin (1 seule exécution IA) :
        1. S'assure que l'état IA est calculé pour la prescription actuelle.
        2. Maintient is_ia_temporary_draft = True si nouveau brouillon non validé.
        3. Renvoie True pour déclencher le rafraîchissement natif des champs du formulaire Odoo JS.
        """
        self.ensure_one()
        patient, medicaments, allergies = self._extract_verification_context()
        if not medicaments:
            self.write({
                FIELD_IA_STATUT: IA_STATUT_NON_VERIFIE,
                FIELD_IA_MESSAGE: False,
                FIELD_IA_FINGERPRINT: False,
                'ia_verified_by_user': True,
            })
            return True

        # Si l'ordonnance n'est pas encore validée et est un nouveau brouillon, marquer is_ia_temporary_draft=True
        write_vals: dict[str, Any] = {'ia_verified_by_user': True}
        if not self.is_validated and (not self.create_date or (datetime.now() - self.create_date).total_seconds() < 300):
            if not self.is_ia_temporary_draft:
                write_vals[FIELD_IS_IA_TEMPORARY_DRAFT] = True

        current_fp = self._compute_ia_fingerprint(medicaments, allergies)
        if self.ia_fingerprint != current_fp or self.ia_statut == IA_STATUT_NON_VERIFIE:
            statut, message, notif = self._calculate_ia_status()
            write_vals.update({
                FIELD_IA_STATUT: statut,
                FIELD_IA_MESSAGE: message,
                FIELD_IA_FINGERPRINT: current_fp,
            })
            self.with_context(in_ia_check=True).write(write_vals)
        else:
            if write_vals:
                self.with_context(in_ia_check=True).write(write_vals)

        return True

    def _show_notification(self, title, message, type_notif) -> bool:
        return True

    # -------------------------------------------------------------------------
    # FILET DE SÉCURITÉ : VÉRIFICATION À L'ENREGISTREMENT FINAL (CREATE / WRITE)
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super(Prescription, self).create(vals_list)
        for record in records:
            if not self.env.context.get('in_ia_check'):
                patient, meds, allergies = record._extract_verification_context()
                if meds:
                    fp = record._compute_ia_fingerprint(meds, allergies)
                    # Si l'analyse n'a pas été effectuée avant sauvegarde ou si composition modifiée
                    if record.ia_fingerprint != fp or record.ia_statut not in (IA_STATUT_SAFE, IA_STATUT_ALLERGY_RISK):
                        statut, message, notif = record._calculate_ia_status()
                        record.with_context(in_ia_check=True).write({
                            FIELD_IA_STATUT: statut,
                            FIELD_IA_MESSAGE: message,
                            FIELD_IA_FINGERPRINT: fp,
                        })
                else:
                    record.with_context(in_ia_check=True).write({
                        FIELD_IA_STATUT: IA_STATUT_NON_VERIFIE,
                        FIELD_IA_MESSAGE: False,
                        FIELD_IA_FINGERPRINT: False,
                    })
            if record.patient_id:
                date_str = record.date_prescription.strftime(DATE_FORMAT) if record.date_prescription else ''
                self.env[NOTIFICATION_MODEL].create_notification(
                    patient_id=record.patient_id.id,
                    title="Nouvelle ordonnance disponible",
                    message=f"Une nouvelle ordonnance a été prescrite pour vous le {date_str}.",
                    notif_type='ordonnance',
                    res_url='/my/ordonnances'
                )
        return records

    def write(self, vals):
        # VERROUILLAGE SERVEUR STRICT : Interdire toute modification d'une ordonnance signée (sauf archivage)
        for record in self:
            if record.state == STATE_SIGNED and not self.env.context.get(FIELD_IN_SIGNATURE_PROCESS):
                # Autoriser uniquement la modification du champ 'active' (pour l'archivage)
                if any(k != FIELD_ACTIVE for k in vals):
                    raise ValidationError(
                        "Cette ordonnance a été signée et est définitivement verrouillée. "
                        "Aucune modification (médicaments, posologies, instructions, date) n'est autorisée sur une ordonnance signée, à l'exception de l'archivage."
                    )

        res = super(Prescription, self).write(vals)
        if not self.env.context.get('in_ia_check') and not self.env.context.get(FIELD_IN_SIGNATURE_PROCESS) and any(k in vals for k in (FIELD_ORDONNANCE_LINE_IDS, FIELD_PATIENT_ID, 'consultation_id', FIELD_ACTIVE)):
            for record in self:
                patient, meds, allergies = record._extract_verification_context()
                if not meds:
                    if record.ia_statut != IA_STATUT_NON_VERIFIE or record.ia_verified_by_user:
                        record.with_context(in_ia_check=True).write({
                            FIELD_IA_STATUT: IA_STATUT_NON_VERIFIE,
                            FIELD_IA_MESSAGE: False,
                            FIELD_IA_FINGERPRINT: False,
                            FIELD_IA_VERIFIED_BY_USER: False,
                        })
                else:
                    fp = record._compute_ia_fingerprint(meds, allergies)
                    if record.ia_fingerprint != fp or record.ia_statut not in (IA_STATUT_SAFE, IA_STATUT_ALLERGY_RISK):
                        statut, message, notif = record._calculate_ia_status()
                        write_data: dict[str, Any] = {
                            FIELD_IA_STATUT: statut,
                            FIELD_IA_MESSAGE: message,
                            FIELD_IA_FINGERPRINT: fp,
                        }
                        if record.ia_fingerprint != fp:
                            write_data[FIELD_IA_VERIFIED_BY_USER] = False
                        record.with_context(in_ia_check=True).write(write_data)
        return res

    def action_open_sign_wizard(self):
        """Ouvre l'assistant de confirmation de signature avec saisie de PIN."""
        self.ensure_one()
        current_user = self.env.user
        
        # 1. Vérification des droits
        if not current_user.has_group(GROUP_MEDECIN):
            raise AccessError("Seul un médecin est autorisé à signer des ordonnances.")

        # 2. Vérification que l'ordonnance contient au moins 1 médicament
        active_lines = self.ordonnance_line_ids.filtered(lambda l: getattr(l, FIELD_ACTIVE, True))
        if not active_lines:
            raise ValidationError("Impossible de signer une ordonnance vide. Veuillez ajouter au moins un médicament.")

        # 3. Vérification que le médecin a configuré sa signature et son PIN
        if not current_user.signature_medecin:
            raise ValidationError(
                "Vous n'avez pas encore enregistré votre image de signature dans votre profil médecin. "
                "Veuillez enregistrer votre signature dans 'Paramètres du cabinet' ou votre profil utilisateur."
            )

        if not current_user.has_signature_pin:
            raise ValidationError(
                "Vous n'avez pas encore configuré votre code PIN secret de signature dans votre profil. "
                "Veuillez définir votre code PIN avant de signer des ordonnances."
            )

        return {
            'name': 'Confirmation de signature',
            KEY_TYPE: ACTION_ACT_WINDOW,
            'res_model': 'cabinet.prescription.sign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_prescription_id': self.id,
            }
        }

    def action_apply_signature(self, doctor_user):
        """Appose la signature immuable du médecin et verrouille définitivement l'ordonnance."""
        self.ensure_one()
        if self.state == STATE_SIGNED:
            raise ValidationError("Cette ordonnance est déjà signée.")

        if not doctor_user.signature_medecin:
            raise ValidationError("Le profil du médecin ne dispose pas d'une signature enregistrée.")

        # Copie immuable de l'image de signature actuelle du médecin
        self.with_context(in_signature_process=True).write({
            FIELD_STATE: STATE_SIGNED,
            'is_signed': True,
            FIELD_IS_VALIDATED: True,
            FIELD_IS_IA_TEMPORARY_DRAFT: False,
            'medecin_signataire_id': doctor_user.id,
            'date_signature': fields.Datetime.now(),
            'signature_image': doctor_user.signature_medecin,
        })
        return True

    def action_save_prescription(self):
        """Action du bouton '💾 Enregistrer l'ordonnance' : validation définitive."""
        self.ensure_one()
        lines = self.ordonnance_line_ids
        active_lines = lines.filtered(lambda l: getattr(l, FIELD_ACTIVE, True)) if hasattr(lines, 'filtered') else [l for l in lines if getattr(l, FIELD_ACTIVE, True)]
        if not active_lines:
            raise ValidationError("Une ordonnance doit contenir au moins un médicament.")
        for line in active_lines:
            med = getattr(line, FIELD_MEDICAMENT, False)
            dos = getattr(line, FIELD_DOSAGE, False)
            pos = getattr(line, FIELD_POSOLOGIE, False)
            if not med or len(str(med).strip()) < 2:
                raise ValidationError("Le nom du médicament doit contenir au moins 2 caractères.")
            if not dos or len(str(dos).strip()) < 1:
                raise ValidationError("Le dosage ne peut pas être vide.")
            if not pos or len(str(pos).strip()) < 5:
                raise ValidationError("La posologie doit contenir au moins 5 caractères.")
        self.write({
            FIELD_IS_VALIDATED: True,
            FIELD_IS_IA_TEMPORARY_DRAFT: False
        })
        return {KEY_TYPE: ACTION_WINDOW_CLOSE}

    def action_cancel_prescription(self):
        """
        Action du bouton '✖ Annuler' :
        - Archiver tout brouillon qui n'a pas été validé définitivement (not is_validated).
        - Protection : si l'ordonnance est déjà signée ou validée, 0 modification.
        """
        for record in self:
            if record.state == STATE_SIGNED:
                raise ValidationError("Une ordonnance signée ne peut pas être annulée.")
            if not record.is_validated:
                record.ordonnance_line_ids.write({FIELD_ACTIVE: False})
                record.write({FIELD_ACTIVE: False})

        return {KEY_TYPE: ACTION_WINDOW_CLOSE}

    def unlink(self):
        """Bloquer la suppression physique directe des ordonnances."""
        for record in self:
            if record.state == STATE_SIGNED:
                raise ValidationError("Impossible de supprimer une ordonnance médicale signée.")
        raise ValidationError("Les ordonnances médicales doivent être conservées à vie pour l'historique pharmacologique. Veuillez les archiver si elles ne sont plus valides.")

    def action_archive_prescription(self):
        self.ensure_one()
        self.write({FIELD_ACTIVE: False})
        return {KEY_TYPE: ACTION_WINDOW_CLOSE}

    def action_unarchive(self):
        """Interdire le désarchivage via le menu Actions."""
        raise ValidationError("Le désarchivage des ordonnances médicales n'est pas autorisé.")



# -------------------------------------------------------------------------
# LIGNE DE PRESCRIPTION (MÉDICAMENT)
# -------------------------------------------------------------------------

class PrescriptionLine(models.Model):
    _rec_name = FIELD_MEDICAMENT
    _name = PRESCRIPTION_LINE_MODEL
    _description = 'Ligne de prescription'
    _order = 'sequence'

    active = fields.Boolean(string='Actif', default=True)
    prescription_id = fields.Many2one(PRESCRIPTION_MODEL, string='Prescription', required=True, ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            presc_id = vals.get(FIELD_PRESCRIPTION_ID)
            if presc_id:
                presc = self.env[PRESCRIPTION_MODEL].browse(presc_id)
                presc_exists = presc.exists() if hasattr(presc, 'exists') else bool(presc)
                if presc_exists and getattr(presc, FIELD_STATE, None) == STATE_SIGNED and not self.env.context.get(FIELD_IN_SIGNATURE_PROCESS):
                    raise ValidationError("Impossible d'ajouter un médicament à une ordonnance déjà signée et verrouillée.")
        return super(PrescriptionLine, self).create(vals_list)

    def write(self, vals):
        for line in self:
            if line.prescription_id and line.prescription_id.state == STATE_SIGNED and not self.env.context.get(FIELD_IN_SIGNATURE_PROCESS):
                raise ValidationError("Impossible de modifier une ligne de médicament sur une ordonnance déjà signée et verrouillée.")
        return super(PrescriptionLine, self).write(vals)

    def unlink(self):
        for line in self:
            if line.prescription_id and line.prescription_id.state == STATE_SIGNED and not self.env.context.get(FIELD_IN_SIGNATURE_PROCESS):
                raise ValidationError("Impossible de supprimer une ligne de médicament d'une ordonnance déjà signée et verrouillée.")
        return super(PrescriptionLine, self).unlink()

    def action_archive(self):
        for line in self:
            if line.prescription_id and line.prescription_id.state == STATE_SIGNED:
                raise ValidationError("Impossible d'archiver une ligne d'une ordonnance déjà signée.")
        self.write({FIELD_ACTIVE: False})

    def action_unarchive(self):
        for line in self:
            if line.prescription_id and line.prescription_id.state == STATE_SIGNED:
                raise ValidationError("Impossible de modifier une ligne d'une ordonnance déjà signée.")
        self.write({FIELD_ACTIVE: True})

    sequence = fields.Integer(string='Séquence', default=10)

    medicament = fields.Char(string='Médicament')
    dosage = fields.Char(string='Dosage', help='Ex: 500mg, 1g, etc.')
    posologie = fields.Text(string='Posologie', help='Ex: 1 comprimé matin et soir pendant 7 jours')
    duree = fields.Char(string='Durée', help='Ex: 7 jours, 1 mois')

    instructions_speciales = fields.Text(string='Instructions spéciales')



    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if FIELD_POSOLOGIE in fields_list:
            defaults[FIELD_POSOLOGIE] = '1 comprimé par jour'
        return defaults

    # Contrôles de saisie
    @api.constrains(FIELD_MEDICAMENT)
    def _check_medicament(self):
        """Vérifier que le nom du médicament n'est pas vide"""
        for rec in self:
            if rec.medicament and len(rec.medicament.strip()) < 2:
                raise ValidationError("Le nom du médicament doit contenir au moins 2 caractères")

    @api.constrains(FIELD_DOSAGE)
    def _check_dosage(self):
        """Vérifier que le dosage est valide"""
        for rec in self:
            if rec.dosage and len(rec.dosage.strip()) < 1:
                raise ValidationError("Le dosage ne peut pas être vide")

    @api.constrains(FIELD_POSOLOGIE)
    def _check_posologie(self):
        """Vérifier que la posologie est suffisamment détaillée"""
        for rec in self:
            if rec.posologie and len(rec.posologie.strip()) < 5:
                raise ValidationError("La posologie doit contenir au moins 5 caractères")

    @api.constrains('sequence')
    def _check_sequence(self):
        """Vérifier que la séquence est positive"""
        for rec in self:
            if rec.sequence and rec.sequence <= 0:
                raise ValidationError("La séquence doit être un nombre positif")

