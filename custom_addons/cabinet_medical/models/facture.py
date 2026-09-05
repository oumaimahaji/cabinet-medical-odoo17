# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError # type: ignore

_logger = logging.getLogger(__name__)

CURRENCY_FIELD = 'currency_id'
DEFAULT_SEQUENCE_NAME = 'Nouveau'
DATE_FORMAT = '%d/%m/%Y'

FACTURE_MODEL = 'cabinet.facture'
NOTIFICATION_MODEL = 'cabinet.notification'
CONFIG_PARAM_MODEL = 'ir.config_parameter'

NOTIF_TITLE_FACTURE = 'Nouvelle facture disponible'
NOTIF_TYPE_FACTURE = 'facture'
NOTIF_URL_FACTURE = '/my/factures'

STATE_DRAFT = 'draft'
STATE_VALIDATED = 'validated'

SCENARIO_SANS_COUVERTURE = 'sans_couverture'
SCENARIO_CNAM_REMBOURSEMENT = 'cnam_remboursement'
SCENARIO_CNAM_TIERS_PAYANT = 'cnam_tiers_payant'
SCENARIO_APCI_TIERS_PAYANT = 'apci_tiers_payant'
SCENARIO_APCI_REMBOURSEMENT = 'apci_remboursement'
SCENARIO_CNAM_REMB_ASSUR = 'cnam_remb_assur'
SCENARIO_CNAM_TP_ASSUR = 'cnam_tp_assur'
SCENARIO_SANS_CNAM_ASSUR = 'sans_cnam_assur'

STATUT_CNAM_NON_ENVOYE = 'non_envoye'
STATUT_CNAM_ENVOYE = 'envoye'
STATUT_CNAM_PAYE = 'paye'
STATUT_CNAM_REJETE = 'rejete'

FILIERE_REMBOURSEMENT = 'remboursement'
FILIERE_PRIVEE = 'privee'
STATUT_ACCORDE = 'accorde'

class Facture(models.Model):
    _name = FACTURE_MODEL
    _description = 'Facture Médicale'
    _order = 'date_facture desc'

    name = fields.Char(string='Numéro facture', readonly=True, default=DEFAULT_SEQUENCE_NAME)
    active = fields.Boolean(string="Actif", default=True)
    patient_id = fields.Many2one('cabinet.patient', string='Patient', required=True)
    consultation_id = fields.Many2one('cabinet.consultation', string='Consultation', required=True)
    date_facture = fields.Date(string='Date', required=True, default=fields.Date.today)
    
    company_id = fields.Many2one(
        'res.company', string='Cabinet', required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        related='company_id.currency_id', readonly=True
    )
    
    # Montants
    montant_total = fields.Monetary(string='Montant total (DT)', currency_field=CURRENCY_FIELD, compute='_compute_montant_total', store=True)
    montant_paye_cabinet = fields.Monetary(string='Payé par le patient (DT)', currency_field=CURRENCY_FIELD, compute='_compute_parts', store=True)
    montant_cnam_cabinet = fields.Monetary(string='Payé par CNAM au cabinet (DT)', currency_field=CURRENCY_FIELD, compute='_compute_parts', store=True)
    reste_a_charge_final = fields.Monetary(string='Reste à charge final patient (DT)', currency_field=CURRENCY_FIELD, compute='_compute_parts', store=True)

    # Montants conventionnels et dépassement CNAM (Groupe 3)
    montant_conventionnel_total = fields.Monetary(
        string='Base conventionnelle totale (TCR DT)',
        currency_field=CURRENCY_FIELD,
        compute='_compute_montant_total',
        store=True,
        help='Montant de référence conventionnel opposable CNAM (Art. 3 Décret 2007-1367)'
    )
    depassement_total = fields.Monetary(
        string='Dépassement total d\'honoraires (DT)',
        currency_field=CURRENCY_FIELD,
        compute='_compute_montant_total',
        store=True,
        help='Part des honoraires excédant le tarif conventionnel à la charge du patient (Art. 17 & 21 Convention)'
    )
    ticket_moderateur_total = fields.Monetary(
        string='Ticket modérateur total (DT)',
        currency_field=CURRENCY_FIELD,
        compute='_compute_parts_display',
        store=True,
        help='Quote-part conventionnelle restant à charge hors dépassement (Art. 20-25 Décret 2007-1367)'
    )
    couverture_depassement_mutuelle = fields.Boolean(
        string='Couverture dépassement mutuelle',
        default=False,
        help='Cocher si le contrat de mutuelle complémentaire prend explicitement en charge les dépassements d\'honoraires'
    )
    
    # Champs d'affichage dynamiques pour la fiche Facture (US15/US16)
    part_cnam_display = fields.Monetary(string='Part CNAM (DT)', currency_field=CURRENCY_FIELD, compute='_compute_parts_display', store=True)
    part_assurance_display = fields.Monetary(string='Part Assurance (DT)', currency_field=CURRENCY_FIELD, compute='_compute_parts_display', store=True)
    reste_apres_cnam_seule = fields.Monetary(string='Reste à charge après CNAM (DT)', currency_field=CURRENCY_FIELD, compute='_compute_parts_display', store=True)

    scenario = fields.Selection([
        (SCENARIO_SANS_COUVERTURE, 'Sans couverture'),
        (SCENARIO_CNAM_REMBOURSEMENT, 'CNAM Remboursement'),
        (SCENARIO_CNAM_TIERS_PAYANT, 'CNAM Tiers-payant'),
        (SCENARIO_APCI_TIERS_PAYANT, 'APCI Tiers-payant (Bordereau)'),
        (SCENARIO_APCI_REMBOURSEMENT, 'APCI Remboursement (BS1)'),
        (SCENARIO_CNAM_REMB_ASSUR, 'CNAM Remboursement + Assurance'),
        (SCENARIO_CNAM_TP_ASSUR, 'CNAM Tiers-payant + Mutuelle (Remboursement Patient)'),
        (SCENARIO_SANS_CNAM_ASSUR, 'Sans CNAM + Assurance'),
    ], string='Scénario de Facturation', compute='_compute_scenario', store=True)

    state = fields.Selection([
        (STATE_DRAFT, 'Brouillon'),
        (STATE_VALIDATED, 'Validée'),
    ], string='État', default=STATE_DRAFT)

    # Lien avec Bordereau M5
    bordereau_id = fields.Many2one('cabinet.bordereau', string='Bordereau CNAM', ondelete='set null')
    statut_cnam = fields.Selection([
        (STATUT_CNAM_NON_ENVOYE, 'Non Envoyé'),
        (STATUT_CNAM_ENVOYE, 'Envoyé (En attente)'),
        (STATUT_CNAM_PAYE, 'Payé'),
        (STATUT_CNAM_REJETE, 'Rejeté')
    ], string='Statut Paiement CNAM', default=STATUT_CNAM_NON_ENVOYE)

    @api.depends(
        'consultation_id.acte_ids.montant',
        'consultation_id.acte_ids.tarif_conventionnel',
        'consultation_id.acte_ids.depassement_honoraire',
        'consultation_id.acte_ids.parametrage_id.tarif',
        'consultation_id.acte_ids.active',
    )
    def _compute_montant_total(self):
        for rec in self:
            consult = getattr(rec, 'consultation_id', None)
            acte_ids = getattr(consult, 'acte_ids', None) if consult else None
            active_actes = acte_ids.filtered(lambda a: a.active) if hasattr(acte_ids, 'filtered') else (acte_ids or [])
            if active_actes:
                rec.montant_total = sum((getattr(a, 'montant', 0.0) or 0.0) for a in active_actes)
                tcr_sum = 0.0
                dep_sum = 0.0
                for a in active_actes:
                    tcr = getattr(a, 'tarif_conventionnel', 0.0)
                    param = getattr(a, 'parametrage_id', None)
                    param_tarif = getattr(param, 'tarif', 0.0) if param else 0.0
                    a_montant = getattr(a, 'montant', 0.0) or 0.0
                    if tcr and isinstance(tcr, (int, float)) and tcr > 0.0:
                        chosen_tcr = tcr
                    elif param_tarif and isinstance(param_tarif, (int, float)) and param_tarif > 0.0:
                        chosen_tcr = param_tarif
                    else:
                        chosen_tcr = a_montant
                    tcr_sum += chosen_tcr
                    dep_sum += max(0.0, (a_montant if isinstance(a_montant, (int, float)) else 0.0) - chosen_tcr)
                rec.montant_conventionnel_total = round(tcr_sum, 2)
                rec.depassement_total = round(dep_sum, 2)
            else:
                rec.montant_total = 0.0
                rec.montant_conventionnel_total = 0.0
                rec.depassement_total = 0.0

    @api.depends('patient_id.is_cnam', 'patient_id.filiere_cnam', 'patient_id.is_apci', 'patient_id.has_assurance')
    def _compute_scenario(self):
        for rec in self:
            p = rec.patient_id
            if p.is_apci and p.filiere_cnam == FILIERE_REMBOURSEMENT:
                rec.scenario = SCENARIO_APCI_REMBOURSEMENT
            elif p.is_apci:
                rec.scenario = SCENARIO_APCI_TIERS_PAYANT
            elif p.is_cnam and p.filiere_cnam == FILIERE_PRIVEE and p.has_assurance:
                rec.scenario = SCENARIO_CNAM_TP_ASSUR
            elif p.is_cnam and p.filiere_cnam == FILIERE_PRIVEE:
                rec.scenario = SCENARIO_CNAM_TIERS_PAYANT
            elif p.is_cnam and p.filiere_cnam == FILIERE_REMBOURSEMENT and p.has_assurance:
                rec.scenario = SCENARIO_CNAM_REMB_ASSUR
            elif p.is_cnam and p.filiere_cnam == FILIERE_REMBOURSEMENT:
                rec.scenario = SCENARIO_CNAM_REMBOURSEMENT
            elif not p.is_cnam and p.has_assurance:
                rec.scenario = SCENARIO_SANS_CNAM_ASSUR
            else:
                rec.scenario = SCENARIO_SANS_COUVERTURE

    def _get_part_cnam_reelle(self):
        self.ensure_one()
        m_total = getattr(self, 'montant_total', 0.0)
        total = m_total if isinstance(m_total, (int, float)) else 0.0
        p = getattr(self, 'patient_id', None)
        if not p or not getattr(p, 'is_cnam', False) or self.scenario in (SCENARIO_SANS_COUVERTURE, SCENARIO_SANS_CNAM_ASSUR):
            return 0.0

        part_cnam = 0.0
        consult = getattr(self, 'consultation_id', None)
        acte_ids = getattr(consult, 'acte_ids', None) if consult else None
        active_actes = acte_ids.filtered(lambda a: a.active) if hasattr(acte_ids, 'filtered') else (acte_ids or [])
        if active_actes:
            ir_config_param = self.env[CONFIG_PARAM_MODEL].sudo()
            taux_default_consult = float(ir_config_param.get_param('cabinet.cnam_taux_consultation', '70.0')) / 100.0
            taux_default_tech = 0.80  # 80% actes médico-chirurgicaux (Art. 21 Décret 2007-1367)
            taux_default_rad_bio = 0.75  # 75% radiologie et biologie (Art. 21 Décret 2007-1367)

            has_explicit_apci_acte = any(getattr(a, 'is_acte_apci', False) for a in active_actes)

            for acte in active_actes:
                # 1. Base TCR conventionnelle de l'acte (Art. 3 Décret 2007-1367)
                tcr = getattr(acte, 'tarif_conventionnel', 0.0)
                param = getattr(acte, 'parametrage_id', None)
                param_tarif = getattr(param, 'tarif', 0.0) if param else 0.0
                a_montant = getattr(acte, 'montant', 0.0) or 0.0
                if tcr and isinstance(tcr, (int, float)) and tcr > 0.0:
                    base_tcr = tcr
                elif param_tarif and isinstance(param_tarif, (int, float)) and param_tarif > 0.0:
                    base_tcr = param_tarif
                else:
                    base_tcr = a_montant if isinstance(a_montant, (int, float)) else 0.0

                # 2. Accord préalable requis non accordé (Convention sectorielle art. 22)
                if getattr(acte, 'necessite_accord_prealable', False) and getattr(acte, 'statut_accord_prealable', 'non_requis') in ('refuse', 'demande'):
                    part_cnam += 0.0
                    continue

                # 3. Éligibilité APCI (100% de la base TCR - Art. 19 Décret 2007-1367)
                is_eligible_apci = False
                if getattr(p, 'is_apci', False):
                    if getattr(acte, 'is_acte_apci', False):
                        is_eligible_apci = True
                    elif has_explicit_apci_acte:
                        # Séance mixte : certains actes sont APCI, d'autres non (Scénario 10)
                        is_eligible_apci = False
                    elif getattr(consult, 'is_consultation_apci', False):
                        is_eligible_apci = True
                    elif 'non_apci' in (getattr(acte, 'description', '') or '').lower() or 'non_apci' in (getattr(consult, 'motif', '') or '').lower() or self.env.context.get('apci_non_liee'):
                        is_eligible_apci = False
                    else:
                        # Rétrocompatibilité Scénarios 4 et 5 (acte unique non différencié sous patient APCI)
                        is_eligible_apci = True

                if is_eligible_apci:
                    part_cnam += base_tcr * 1.0
                    continue

                # 4. Taux CNAM de droit commun selon le type d'acte et paramétrage
                param = getattr(acte, 'parametrage_id', None)
                taux_cnam = getattr(param, 'taux_cnam', None) if param else None
                if param and taux_cnam is not None and taux_cnam is not False:
                    taux = float(taux_cnam) / 100.0
                else:
                    type_a = getattr(acte, 'type_acte', 'consultation')
                    if type_a in ('acte_technique', 'chirurgie', 'suture'):
                        taux = taux_default_tech
                    elif type_a in ('radiologie', 'biologie'):
                        taux = taux_default_rad_bio
                    else:
                        taux = taux_default_consult

                part_cnam += base_tcr * taux
        else:
            ir_config_param = self.env[CONFIG_PARAM_MODEL].sudo()
            taux_remb_pct = float(ir_config_param.get_param('cabinet.cnam_taux_remboursement', '70.0')) / 100.0
            m_conv = getattr(self, 'montant_conventionnel_total', None)
            base_tcr = m_conv if (isinstance(m_conv, (int, float)) and m_conv > 0) else total
            part_cnam = base_tcr * taux_remb_pct

        return round(part_cnam, 2)

    @api.depends(
        'montant_total', 'montant_conventionnel_total', 'depassement_total', 'scenario',
        'couverture_depassement_mutuelle',
        'patient_id.assurance_taux', 'patient_id.has_assurance',
        'consultation_id.acte_ids',
        'consultation_id.acte_ids.montant',
        'consultation_id.acte_ids.tarif_conventionnel',
        'consultation_id.acte_ids.depassement_honoraire',
        'consultation_id.acte_ids.is_acte_apci',
        'consultation_id.acte_ids.statut_accord_prealable',
        'consultation_id.acte_ids.active',
        'consultation_id.acte_ids.parametrage_id',
        'consultation_id.acte_ids.parametrage_id.taux_cnam',
    )
    def _compute_parts(self):
        for rec in self:
            m_total = getattr(rec, 'montant_total', 0.0)
            total = m_total if isinstance(m_total, (int, float)) else 0.0

            m_conv = getattr(rec, 'montant_conventionnel_total', None)
            tcr_total = m_conv if (isinstance(m_conv, (int, float)) and m_conv > 0) else total

            m_dep = getattr(rec, 'depassement_total', None)
            depassement = m_dep if isinstance(m_dep, (int, float)) else max(0.0, total - tcr_total)

            p = getattr(rec, 'patient_id', None)
            assur_taux = getattr(p, 'assurance_taux', 0.0) if p else 0.0
            taux_assur = (assur_taux if isinstance(assur_taux, (int, float)) else 0.0) / 100.0

            assurance_id = getattr(p, 'assurance_id', None) if p else None
            tp_direct = getattr(assurance_id, 'tiers_payant_direct', False) if assurance_id else False

            part_cnam_reelle = rec._get_part_cnam_reelle()
            if not isinstance(part_cnam_reelle, (int, float)):
                part_cnam_reelle = 0.0

            # Le ticket modérateur conventionnel ne s'applique que sur la base conventionnelle
            ticket_mod_conventionnel = max(0.0, tcr_total - part_cnam_reelle)

            # La mutuelle intervient en priorité sur le ticket modérateur
            part_mutuelle_tm = ticket_mod_conventionnel * taux_assur
            # Le dépassement n'est couvert par la mutuelle QUE si explicitement configuré
            couv_dep = getattr(rec, 'couverture_depassement_mutuelle', False)
            part_mutuelle_dep = (depassement * taux_assur) if (couv_dep is True) else 0.0
            part_mutuelle_totale = part_mutuelle_tm + part_mutuelle_dep

            if rec.scenario == SCENARIO_SANS_COUVERTURE:
                rec.montant_paye_cabinet = round(total, 2)
                rec.montant_cnam_cabinet = 0.0
                rec.reste_a_charge_final = round(total, 2)

            elif rec.scenario == SCENARIO_APCI_TIERS_PAYANT:
                rec.montant_cnam_cabinet = round(part_cnam_reelle, 2)
                rec.montant_paye_cabinet = round(ticket_mod_conventionnel + depassement, 2)
                rec.reste_a_charge_final = round(ticket_mod_conventionnel + depassement, 2)

            elif rec.scenario == SCENARIO_APCI_REMBOURSEMENT:
                rec.montant_cnam_cabinet = 0.0
                rec.montant_paye_cabinet = round(total, 2)
                rec.reste_a_charge_final = round(ticket_mod_conventionnel + depassement, 2)

            elif rec.scenario in (SCENARIO_CNAM_TIERS_PAYANT, SCENARIO_CNAM_TP_ASSUR):
                rec.montant_cnam_cabinet = round(part_cnam_reelle, 2)
                if rec.scenario == SCENARIO_CNAM_TP_ASSUR:
                    if tp_direct:
                        rec.montant_paye_cabinet = round((ticket_mod_conventionnel - part_mutuelle_tm) + (depassement - part_mutuelle_dep), 2)
                    else:
                        rec.montant_paye_cabinet = round(ticket_mod_conventionnel + depassement, 2)
                    rec.reste_a_charge_final = round((ticket_mod_conventionnel - part_mutuelle_tm) + (depassement - part_mutuelle_dep), 2)
                else:
                    rec.montant_paye_cabinet = round(ticket_mod_conventionnel + depassement, 2)
                    rec.reste_a_charge_final = round(ticket_mod_conventionnel + depassement, 2)

            elif rec.scenario == SCENARIO_CNAM_REMBOURSEMENT:
                rec.montant_paye_cabinet = round(total, 2)
                rec.montant_cnam_cabinet = 0.0
                rec.reste_a_charge_final = round(ticket_mod_conventionnel + depassement, 2)

            elif rec.scenario == SCENARIO_CNAM_REMB_ASSUR:
                rec.montant_cnam_cabinet = 0.0
                if tp_direct:
                    rec.montant_paye_cabinet = round(total - part_mutuelle_totale, 2)
                else:
                    rec.montant_paye_cabinet = round(total, 2)
                rec.reste_a_charge_final = round((ticket_mod_conventionnel - part_mutuelle_tm) + (depassement - part_mutuelle_dep), 2)

            elif rec.scenario == SCENARIO_SANS_CNAM_ASSUR:
                rec.montant_cnam_cabinet = 0.0
                part_assur_sans_cnam = total * taux_assur
                if tp_direct:
                    rec.montant_paye_cabinet = round(total - part_assur_sans_cnam, 2)
                else:
                    rec.montant_paye_cabinet = round(total, 2)
                rec.reste_a_charge_final = round(total - part_assur_sans_cnam, 2)

    @api.depends(
        'scenario', 'montant_total', 'montant_conventionnel_total', 'depassement_total',
        'montant_cnam_cabinet', 'montant_paye_cabinet', 'reste_a_charge_final',
        'couverture_depassement_mutuelle',
        'patient_id.assurance_taux', 'patient_id.has_assurance',
        'consultation_id.acte_ids',
        'consultation_id.acte_ids.montant',
        'consultation_id.acte_ids.tarif_conventionnel',
        'consultation_id.acte_ids.depassement_honoraire',
        'consultation_id.acte_ids.is_acte_apci',
        'consultation_id.acte_ids.statut_accord_prealable',
        'consultation_id.acte_ids.active',
        'consultation_id.acte_ids.parametrage_id',
        'consultation_id.acte_ids.parametrage_id.taux_cnam',
    )
    def _compute_parts_display(self):
        for rec in self:
            m_total = getattr(rec, 'montant_total', 0.0)
            total = m_total if isinstance(m_total, (int, float)) else 0.0

            m_conv = getattr(rec, 'montant_conventionnel_total', None)
            tcr_total = m_conv if (isinstance(m_conv, (int, float)) and m_conv > 0) else total

            m_dep = getattr(rec, 'depassement_total', None)
            depassement = m_dep if isinstance(m_dep, (int, float)) else max(0.0, total - tcr_total)

            p = getattr(rec, 'patient_id', None)
            assur_taux = getattr(p, 'assurance_taux', 0.0) if p else 0.0
            taux_assur = (assur_taux if isinstance(assur_taux, (int, float)) else 0.0) / 100.0

            part_cnam_reelle = rec._get_part_cnam_reelle()
            if not isinstance(part_cnam_reelle, (int, float)):
                part_cnam_reelle = 0.0

            ticket_mod = max(0.0, tcr_total - part_cnam_reelle)

            part_cnam = 0.0
            part_assurance = 0.0

            if rec.scenario == SCENARIO_SANS_COUVERTURE:
                part_cnam = 0.0
                part_assurance = 0.0
            elif rec.scenario in (SCENARIO_APCI_TIERS_PAYANT, SCENARIO_APCI_REMBOURSEMENT):
                part_cnam = part_cnam_reelle
                part_assurance = 0.0
            elif rec.scenario in (SCENARIO_CNAM_TIERS_PAYANT, SCENARIO_CNAM_TP_ASSUR):
                part_cnam = part_cnam_reelle
                if rec.scenario == SCENARIO_CNAM_TP_ASSUR:
                    couv_dep = getattr(rec, 'couverture_depassement_mutuelle', False)
                    part_mutuelle_dep = (depassement * taux_assur) if (couv_dep is True) else 0.0
                    part_assurance = (ticket_mod * taux_assur) + part_mutuelle_dep
            elif rec.scenario == SCENARIO_CNAM_REMBOURSEMENT:
                part_cnam = part_cnam_reelle
                part_assurance = 0.0
            elif rec.scenario == SCENARIO_CNAM_REMB_ASSUR:
                part_cnam = part_cnam_reelle
                couv_dep = getattr(rec, 'couverture_depassement_mutuelle', False)
                part_mutuelle_dep = (depassement * taux_assur) if (couv_dep is True) else 0.0
                part_assurance = (ticket_mod * taux_assur) + part_mutuelle_dep
            elif rec.scenario == SCENARIO_SANS_CNAM_ASSUR:
                part_cnam = 0.0
                part_assurance = total * taux_assur

            rec.part_cnam_display = round(part_cnam, 2)
            rec.part_assurance_display = round(part_assurance, 2)
            rec.ticket_moderateur_total = round(ticket_mod, 2)
            rec.reste_apres_cnam_seule = round(max(0.0, total - part_cnam), 2)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', DEFAULT_SEQUENCE_NAME) == DEFAULT_SEQUENCE_NAME:
                vals['name'] = self.env['ir.sequence'].next_by_code(FACTURE_MODEL) or DEFAULT_SEQUENCE_NAME
        records = super(Facture, self).create(vals_list)
        for record in records:
            if record.state == STATE_VALIDATED and record.patient_id:
                self.env[NOTIFICATION_MODEL].create_notification(
                    patient_id=record.patient_id.id,
                    title=NOTIF_TITLE_FACTURE,
                    message=f"La facture {record.name} d'un montant de {record.montant_total} DT est disponible.",
                    notif_type=NOTIF_TYPE_FACTURE,
                    res_url=NOTIF_URL_FACTURE
                )
        return records

    LOCKED_FIELDS_VALIDATED = {'patient_id', 'consultation_id', 'date_facture', 'scenario'}

    def unlink(self):
        for rec in self:
            if rec.state == STATE_VALIDATED:
                raise ValidationError("Suppression interdite : La facture %s est validée et constitue une pièce comptable immuable." % (rec.name or ''))
            if getattr(rec, 'bordereau_id', False):
                raise ValidationError("Suppression interdite : La facture %s est rattachée au bordereau CNAM %s." % (rec.name or '', rec.bordereau_id.name or ''))
        return super(Facture, self).unlink()

    def write(self, vals):
        for rec in self:
            if rec.state == STATE_VALIDATED and not self.env.context.get('bypass_facture_lock'):
                locked_modified = set(vals.keys()) & self.LOCKED_FIELDS_VALIDATED
                if locked_modified:
                    raise ValidationError("Modification interdite : La facture %s est validée. Les champs suivants sont verrouillés : %s." % (rec.name or '', ', '.join(locked_modified)))
                if rec.bordereau_id and 'bordereau_id' in vals and vals['bordereau_id'] != rec.bordereau_id.id and not self.env.su:
                    raise ValidationError("Modification interdite : La facture %s est déjà rattachée au bordereau %s." % (rec.name or '', rec.bordereau_id.name or ''))

        pre_vals = {getattr(rec, 'id'): rec.state for rec in self}
        res = super(Facture, self).write(vals)
        if 'state' in vals:
            for record in self:
                old_state = pre_vals.get(getattr(record, 'id'))
                if old_state != STATE_VALIDATED and record.state == STATE_VALIDATED and record.patient_id:
                    self.env[NOTIFICATION_MODEL].create_notification(
                        patient_id=record.patient_id.id,
                        title=NOTIF_TITLE_FACTURE,
                        message=f"La facture {record.name} d'un montant de {record.montant_total} DT est disponible.",
                        notif_type=NOTIF_TYPE_FACTURE,
                        res_url=NOTIF_URL_FACTURE
                    )
        return res

    def action_valider(self):
        self.ensure_one()
        m_tot = getattr(self, 'montant_total', 0.0)
        if (m_tot if isinstance(m_tot, (int, float)) else 0.0) <= 0:
            raise ValidationError("Le montant total doit être supérieur à 0")

        # Contrôles bloquants CNAM (Groupe 4)
        date_ref = getattr(self, 'date_facture', False) or fields.Date.context_today(self)
        p = getattr(self, 'patient_id', None)

        if self.scenario in (SCENARIO_CNAM_TIERS_PAYANT, SCENARIO_APCI_TIERS_PAYANT, SCENARIO_CNAM_TP_ASSUR):
            if not p:
                raise ValidationError("Validation impossible : Aucun patient rattaché à la facture.")
            if not getattr(p, 'is_cnam', False):
                raise ValidationError("Validation impossible en Tiers-payant : Le patient n'est pas identifié comme assuré CNAM.")

            # 1. Vérification de la date d'expiration des droits CNAM
            validite_cnam = getattr(p, 'date_validite_cnam', False)
            if validite_cnam and validite_cnam < date_ref:
                date_str = validite_cnam.strftime(DATE_FORMAT) if hasattr(validite_cnam, 'strftime') else str(validite_cnam)
                ref_str = date_ref.strftime(DATE_FORMAT) if hasattr(date_ref, 'strftime') else str(date_ref)
                raise ValidationError(f"Validation impossible en Tiers-payant : Les droits CNAM de l'assuré {p.name} sont expirés depuis le {date_str} (date de facturation : {ref_str}). Le tiers-payant ne peut pas être appliqué.")

            # 2. Vérification APCI : Décision et date de validité
            consult = getattr(self, 'consultation_id', None)
            acte_ids = getattr(consult, 'acte_ids', None) if consult else None
            active_actes = acte_ids.filtered(lambda a: a.active) if hasattr(acte_ids, 'filtered') else (acte_ids or [])
            has_apci_acte = any(getattr(a, 'is_acte_apci', False) for a in active_actes)

            if self.scenario == SCENARIO_APCI_TIERS_PAYANT or has_apci_acte:
                if not getattr(p, 'is_apci', False):
                    raise ValidationError(f"Validation impossible en APCI : Le patient {p.name} n'est pas enregistré comme bénéficiaire de l'APCI.")
                if not getattr(p, 'numero_decision_apci', False):
                    raise ValidationError(f"Validation impossible : Le patient {p.name} n'a aucun numéro de décision APCI valide.")
                date_fin_apci = getattr(p, 'date_fin_apci', False)
                if date_fin_apci and date_fin_apci < date_ref:
                    date_fin_str = date_fin_apci.strftime(DATE_FORMAT) if hasattr(date_fin_apci, 'strftime') else str(date_fin_apci)
                    raise ValidationError(f"Validation impossible en APCI : La prise en charge APCI de {p.name} est expirée depuis le {date_fin_str}.")

            # 3. Contrôle Accord préalable obligatoire pour les actes conventionnés
            for a in active_actes:
                if getattr(a, 'necessite_accord_prealable', False):
                    statut_ap = getattr(a, 'statut_accord_prealable', 'non_requis')
                    num_ap = getattr(a, 'numero_accord_prealable', False)
                    if statut_ap != STATUT_ACCORDE and not num_ap:
                        desc = getattr(a, 'description', '') or getattr(a, 'type_acte', 'Acte conventionné')
                        raise ValidationError(f"Validation impossible en Tiers-payant : L'acte '{desc}' requiert un accord préalable obligatoire de la CNAM (statut actuel : '{statut_ap}'). Un accord préalable accordé est obligatoire pour la prise en charge en tiers-payant.")

        self.state = STATE_VALIDATED

    # --- IA n°3 : Assistant LLM pour la reformulation des alertes ---
    @api.model
    def _get_llm_alert(self, anomaly_type, context_data, default_message):
        """ Envoie le contexte à Ollama en local pour reformuler l'alerte en langage naturel """
        import requests # type: ignore
        import time
        ir_config_param = self.env['ir.config_parameter'].sudo()
        url = ir_config_param.get_param('cabinet_medical.ollama_url', 'http://ollama:11434/api/generate')
        model = ir_config_param.get_param('cabinet_medical.ollama_model', 'tinyllama')
        prompt = f"""Tu es l'assistant médical intelligent d'un cabinet médical Odoo.
Alerte : {anomaly_type}
Contexte technique : {context_data}
Message par défaut : {default_message}
Consigne : Rédige une seule phrase d'alerte claire, fluide et professionnelle en français pour la secrétaire médicale. Intègre impérativement tous les détails concrets pertinents fournis dans le contexte (nom du patient, délais en jours, pathologie, référence/décision). Réponds directement sans préambule ni guillemets."""

        start_time = time.time()
        try:
            # Timeout : 1.5s connexion TCP, 15.0s max réponse LLM + keep_alive permanent
            response = requests.post(url, json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": -1,
                "options": {
                    "num_predict": 95,
                    "temperature": 0.1,
                }
            }, timeout=(1.5, 15.0))
            
            if response.status_code == 200:
                result = response.json()
                if 'response' in result and result['response']:
                    cleaned_resp = result['response'].strip().strip('"').strip("'")
                    return f"✨ [IA Assistant] : {cleaned_resp}"
        except Exception as e:
            elapsed = time.time() - start_time
            _logger.warning(
                "Ollama/Phi3 _get_llm_alert failed after %.2fs (%s: %s). Fallback to default message.",
                elapsed, type(e).__name__, e
            )
            
        return default_message

    # --- IA n°2 & 3 : Détection d'anomalie & Assistant LLM ---
    @api.constrains('patient_id')
    def _check_apci_decision(self):
        for rec in self:
            if rec.patient_id.is_apci and not rec.patient_id.numero_decision_apci:
                default_msg = "Anomalie 3 : APCI sans décision. Le statut APCI est activé mais aucune décision CNAM n'est enregistrée pour ce patient."
                context = f"Patient: {rec.patient_id.name}, APCI activé, Décision non fournie"
                alert = self._get_llm_alert("Patient APCI sans décision formelle", context, default_msg)
                raise ValidationError(alert)
