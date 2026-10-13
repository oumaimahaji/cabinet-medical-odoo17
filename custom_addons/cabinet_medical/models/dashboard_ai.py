import json
import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import Counter
from typing import Any, Dict
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

JSON_BLOCK_DELIMITER = "```json"
CODE_BLOCK_DELIMITER = "```"

class DashboardAI(models.AbstractModel):
    _name = 'cabinet.dashboard.ai'
    _description = 'Assistant IA du Tableau de Bord'

    @api.model
    def get_ai_insights(self):
        """
        Méthode principale d'orchestration de l'Assistant IA.
        Appelle les méthodes modulaires pour collecter les données,
        calcule les scores et anomalies, et sollicite l'IA.
        """
        _logger.info("\n\n\n[!!!] GET_AI_INSIGHTS HAS BEEN CALLED BY THE BROWSER! [!!!]\n\n\n")
        is_medecin = self.env.user.has_group('cabinet_medical.group_medecin')
        
        today = fields.Date.context_today(self)
        first_day_month = today.replace(day=1)
        first_day_last_month = (first_day_month - timedelta(days=1)).replace(day=1)
        last_day_last_month = first_day_month - timedelta(days=1)
        
        if is_medecin:
            metrics = self._collect_base_metrics(today, first_day_month, first_day_last_month, last_day_last_month)
            med_metrics = self._collect_medical_metrics(first_day_month)
            metrics.update(med_metrics)
            
            # Algorithmes Locaux (Fallback & Contexte pour l'IA)
            self._calculate_health_index(metrics)
            self._detect_anomalies(metrics)
            self._compute_forecasts(metrics)
            self._generate_recommendations(metrics)
            
            return self._call_ia_api(metrics, is_medecin)
        else:
            # Sécrétaire
            metrics = self._collect_secretaire_metrics(today, first_day_month, first_day_last_month, last_day_last_month)
            return self._call_ia_api(metrics, False)

    # ---------------------------------------------------------
    # 1. COLLECTE DE DONNÉES (MODULARISÉE POUR LA SOUTENANCE)
    # ---------------------------------------------------------

    def _collect_base_metrics(self, today, first_day_month, first_day_last_month, last_day_last_month):
        """Collecte les indicateurs d'activité globaux et financiers (Médecin)."""
        metrics: dict[str, Any] = {'isMedecin': True}
        
        # Consultations (chiffres globaux du cabinet via sudo pour cohérence stricte cron/dashboard)
        metrics['consults_jour'] = self.env['cabinet.consultation'].sudo().search_count([('date_consultation', '=', today)])
        metrics['consults_ce_mois'] = self.env['cabinet.consultation'].sudo().search_count([('date_consultation', '>=', first_day_month)])
        metrics['consults_mois_dernier'] = self.env['cabinet.consultation'].sudo().search_count([
            ('date_consultation', '>=', first_day_last_month),
            ('date_consultation', '<=', last_day_last_month)
        ])
        metrics['tendance_consults'] = metrics['consults_ce_mois'] - metrics['consults_mois_dernier']
        
        # Impayés patients
        factures_impayees = self.env['cabinet.facture'].sudo().search([('state', '=', 'validated'), ('reste_a_charge_final', '>', 0)])
        metrics['impayes_patients'] = round(sum(f.reste_a_charge_final for f in factures_impayees), 3)
        metrics['nb_factures_impayees'] = len(factures_impayees)
        
        # Facturation (mois en cours et mois précédent pour analyse de tendance réelle)
        metrics['factures_ce_mois'] = self.env['cabinet.facture'].sudo().search_count([
            ('state', '=', 'validated'), ('date_facture', '>=', first_day_month)
        ])
        metrics['factures_mois_dernier'] = self.env['cabinet.facture'].sudo().search_count([
            ('state', '=', 'validated'), ('date_facture', '>=', first_day_last_month), ('date_facture', '<=', last_day_last_month)
        ])
        
        # Total patients
        metrics['patients_total'] = self.env['cabinet.patient'].sudo().search_count([])
        
        # Profils Patients
        patients_du_mois = self.env['cabinet.consultation'].sudo().search([('date_consultation', '>=', first_day_month)]).mapped('patient_id')
        profils = [p.profil_couverture for p in patients_du_mois if p.profil_couverture]
        profil_dominant_key = max(set(profils), key=profils.count) if profils else 'aucun'
        metrics['profil_dominant'] = dict(self.env['cabinet.patient']._fields['profil_couverture'].selection).get(profil_dominant_key, 'Aucun')
        
        # Graphes (US35, US36, US37, US39)
        self._prepare_chart_data(today, metrics)
        
        return metrics

    def _collect_medical_metrics(self, first_day_month):
        """Collecte les métriques pures issues de l'IA Médicale du PFE (Allergies, Médicaments)."""
        med_metrics: dict[str, Any] = {}
        
        # BUG FIX #1 (date) : On utilise une fenêtre GLISSANTE de 30 jours
        # au lieu du mois calendaire strict (first_day_month).
        # Raison : si une alerte Amoxicilline a été émise le 24 juin
        # et qu'on est le 7 juillet, elle serait exclue par first_day_month=2026-07-01.
        # Avec 30 jours glissants, elle reste visible et pertinente cliniquement.
        from datetime import timedelta
        today = fields.Date.context_today(self)
        fenetre_30j = today - timedelta(days=30)
        ordonnances = self.env['cabinet.prescription'].sudo().search(
            [('date_prescription', '>=', fenetre_30j)]
        )
        
        nb_alertes = 0
        nb_alertes_critiques = 0
        meds_prescrits = []
        
        for ordo in ordonnances:
            if ordo.ia_statut == 'allergy_risk':
                nb_alertes += 1
                if ordo.ia_message and (
                    '100%' in ordo.ia_message
                    or '90%' in ordo.ia_message
                    or 'critique' in ordo.ia_message.lower()
                ):
                    nb_alertes_critiques += 1
            for ligne in ordo.ordonnance_line_ids:
                if ligne.medicament:
                    meds_prescrits.append(ligne.medicament)
                    
        med_metrics['nb_alertes_allergies'] = nb_alertes
        med_metrics['nb_alertes_critiques'] = nb_alertes_critiques
        
        # Médicaments les plus prescrits
        top_meds = [med for med, count in Counter(meds_prescrits).most_common(3)]
        med_metrics['top_medicaments'] = ", ".join(top_meds) if top_meds else "Aucun"
        
        # Taux de consultation avec/sans ordonnance
        consults = self.env['cabinet.consultation'].sudo().search([('date_consultation', '>=', first_day_month)])
        avec_ordo = sum(1 for c in consults if c.prescription_ids)
        sans_ordo = len(consults) - avec_ordo
        med_metrics['consults_avec_ordo'] = avec_ordo
        med_metrics['consults_sans_ordo'] = sans_ordo
        
        # Patients à risque (ayant des allergies)
        patients = self.env['cabinet.patient'].sudo().search([('allergies', '!=', False)])
        med_metrics['patients_allergiques'] = len(patients)
        
        return med_metrics

    def _prepare_chart_data(self, today, metrics):
        """Prépare les tableaux de données pour Chart.js (6 mois d'historique)."""
        months_labels = []
        consults_data = []
        cnam_attente_data = []
        
        for i in range(5, -1, -1):
            d = today - relativedelta(months=i)
            start = d.replace(day=1)
            end = (start + relativedelta(months=1)) - timedelta(days=1)
            months_labels.append(start.strftime('%b %Y'))
            
            # Consultations
            count = self.env['cabinet.consultation'].search_count([('date_consultation', '>=', start), ('date_consultation', '<=', end)])
            consults_data.append(count)
            
            # CNAM Attente
            factures_attente = self.env['cabinet.facture'].search([
                ('state', '=', 'validated'),
                ('scenario', 'in', ['cnam_tiers_payant', 'apci_tiers_payant', 'cnam_tp_assur']),
                ('statut_cnam', '!=', 'paye'),
                ('date_facture', '>=', start),
                ('date_facture', '<=', end)
            ])
            cnam_attente_data.append(sum(f.montant_cnam_cabinet for f in factures_attente))
            
        metrics['us35_labels'] = months_labels
        metrics['us35_data'] = consults_data
        metrics['us37_labels'] = months_labels
        metrics['us37_data'] = cnam_attente_data
        
        # US36: CA ventilé par catégorie de couverture
        # BUG FIX #2 : Les slugs 'sans_cnam' et 'apci_exoneration' n'existent PAS dans facture.py.
        # Les vraies valeurs de scenario (Selection field) sont :
        #   'sans_couverture', 'sans_cnam_assur'
        #   'cnam_remboursement', 'cnam_remb_assur'
        #   'cnam_tiers_payant', 'cnam_tp_assur'
        #   'apci_tiers_payant', 'apci_remboursement'
        # On regroupe les 8 scénarios en 4 catégories lisibles pour le graphe.
        ca_data = [0.0, 0.0, 0.0, 0.0]
        factures_ca = self.env['cabinet.facture'].search([('state', '=', 'validated')])
        for f in factures_ca:
            s = f.scenario
            if s in ('sans_couverture', 'sans_cnam_assur'):
                # Catégorie 0 : Patients sans couverture CNAM (avec ou sans assurance privée)
                ca_data[0] += f.montant_total
            elif s in ('cnam_remboursement', 'cnam_remb_assur'):
                # Catégorie 1 : CNAM Remboursement (patient avance, CNAM rembourse)
                ca_data[1] += f.montant_total
            elif s in ('cnam_tiers_payant', 'cnam_tp_assur'):
                # Catégorie 2 : CNAM Tiers-Payant (CNAM paie directement au cabinet)
                ca_data[2] += f.montant_total
            elif s in ('apci_tiers_payant', 'apci_remboursement'):
                # Catégorie 3 : APCI / Exonération (patients exonérés totalement)
                ca_data[3] += f.montant_total
        metrics['us36_labels'] = ['Sans CNAM', 'CNAM Remboursement', 'CNAM Tiers-Payant', 'APCI']
        metrics['us36_data'] = [round(v, 3) for v in ca_data]
        
        # US39: Camembert répartition patients
        patients_all = self.env['cabinet.patient'].search([])
        nb_sans = sum(1 for p in patients_all if not p.is_cnam)
        nb_apci = sum(1 for p in patients_all if p.is_apci)
        nb_cnam = sum(1 for p in patients_all if p.is_cnam and not p.is_apci)
        metrics['us39_labels'] = ["CNAM", "APCI", "Sans couverture"]
        metrics['us39_data'] = [nb_cnam, nb_apci, nb_sans]

    def _collect_secretaire_metrics(self, today, first_day_month, first_day_last_month, last_day_last_month):
        """Collecte les indicateurs pour la vue Secrétaire/Gestionnaire.
        
        Retourne tous les champs attendus par le template OWL ai_dashboard.xml :
          - consults_semaine, impayes_montant, jours_attente_moyens, rejetes_mois
          - taux_cnam, patients_crees_mois, rdv_confirmes, rdv_annules
          - montant_encaisse_mois, taux_dossiers_incomplets, dossiers_incomplets_count
          - rdvs_today (liste de dicts pour le tableau de RDV du jour)
        """
        from datetime import timedelta

        m: dict[str, Any] = {'isMedecin': False}

        # Fenetre glissante 30 jours — meme logique que les alertes allergies medecin.
        # Les factures/RDV du mois precedent recents restent visibles meme en debut de mois.
        # (Ex: factures du 24 juin sont encore pertinentes le 7 juillet)
        fenetre_30j = today - timedelta(days=30)

        # ── 1. Consultations de la semaine ────────────────────────────────────
        debut_semaine = today - timedelta(days=today.weekday())  # lundi courant
        m['consults_semaine'] = self.env['cabinet.consultation'].search_count([
            ('date_consultation', '>=', debut_semaine),
            ('date_consultation', '<=', today),
        ])

        # ── 2. Impayés CNAM (factures validées tiers-payant non payées) ───────
        factures_cnam_attente = self.env['cabinet.facture'].search([
            ('state', '=', 'validated'),
            ('scenario', 'in', ['cnam_tiers_payant', 'cnam_tp_assur', 'apci_tiers_payant']),
            ('statut_cnam', 'not in', ['paye']),
        ])
        m['impayes_montant'] = round(sum(f.montant_cnam_cabinet for f in factures_cnam_attente), 3)

        # Jours d'attente moyens CNAM (depuis date_facture)
        if factures_cnam_attente:
            jours = [(today - f.date_facture).days for f in factures_cnam_attente if f.date_facture]
            m['jours_attente_moyens'] = round(sum(jours) / len(jours), 0) if jours else 0
        else:
            m['jours_attente_moyens'] = 0

        # ── 3. Bordereaux/factures rejetées (fenetre 30j) ────────────────────
        m['rejetes_mois'] = self.env['cabinet.facture'].search_count([
            ('statut_cnam', '=', 'rejete'),
            ('date_facture', '>=', fenetre_30j),
        ])

        # ── 4. Taux patients CNAM ─────────────────────────────────────────────
        total_patients = self.env['cabinet.patient'].search_count([])
        cnam_patients  = self.env['cabinet.patient'].search_count([('is_cnam', '=', True)])
        m['taux_cnam'] = round((cnam_patients / total_patients * 100), 1) if total_patients else 0

        # ── 5. Nouveaux patients créés ce mois ───────────────────────────────
        # On compte via create_date (champ système automatique sur tout modèle Odoo)
        m['patients_crees_mois'] = self.env['cabinet.patient'].search_count([
            ('create_date', '>=', fields.Datetime.to_string(
                fields.Datetime.from_string(str(first_day_month) + ' 00:00:00')
            )),
        ])

        # ── 6. RDV annulés / confirmés (fenetre 30j) ─────────────────────────
        rdvs_mois = self.env['cabinet.rendezvous'].search([
            ('date', '>=', fenetre_30j),
            ('date', '<=', today),
        ])
        m['rdv_annules']   = sum(1 for r in rdvs_mois if r.state == 'annule')
        m['rdv_confirmes'] = sum(1 for r in rdvs_mois if r.state not in ('annule', 'absent'))
        # BUG FIX #2 (NaN) : pré-calcul du total pour éviter undefined+undefined en JS
        m['rdv_total']     = m['rdv_confirmes'] + m['rdv_annules']

        # ── 7. Montant encaissé (fenetre 30j) ────────────────────────────────
        # BUG FIX : filtre 'date_facture >= first_day_month' excluait les factures
        # du mois precedent (ex: 2026-06-24 invisible depuis le 2026-07-01).
        # Solution : fenetre glissante 30j identique a celle des alertes allergies.
        factures_mois = self.env['cabinet.facture'].search([
            ('state', '=', 'validated'),
            ('date_facture', '>=', fenetre_30j),
        ])
        m['montant_encaisse_mois'] = round(sum(f.montant_paye_cabinet for f in factures_mois), 3)

        # ── 8. Dossiers incomplets ────────────────────────────────────────────
        patients_all = self.env['cabinet.patient'].search([])
        incomplets   = [p for p in patients_all if not p.is_dossier_complet]
        m['dossiers_incomplets_count'] = len(incomplets)
        m['taux_dossiers_incomplets']  = round(len(incomplets) / len(patients_all) * 100, 1) if patients_all else 0

        # ── 9. RDV du jour (tableau) ──────────────────────────────────────────
        rdvs_today = self.env['cabinet.rendezvous'].search([
            ('date', '=', today),
        ], order='heure asc')

        rdvs_list = []
        for rdv in rdvs_today:
            h = int(rdv.heure)
            mn = int(round((rdv.heure - h) * 60))
            rdvs_list.append({
                'heure':   f"{h:02d}:{mn:02d}",
                'patient': rdv.display_patient_name or '—',
                'motif':   rdv.motif_rapide or '—',
                'statut':  dict(self.env['cabinet.rendezvous']._fields['state'].selection).get(rdv.state, rdv.state),
            })
        m['rdvs_today'] = rdvs_list

        # ── 10. Génération HTML insights secrétaire ───────────────────────────
        taux_annul = 0
        total_rdv = m['rdv_confirmes'] + m['rdv_annules']
        if total_rdv > 0:
            taux_annul = round(m['rdv_annules'] / total_rdv * 100, 1)

        html = f"""
        <ul class='list-unstyled mb-0'>
            <li class='mb-2'><strong>📅 Agenda du jour :</strong> {len(rdvs_list)} rendez-vous programmés aujourd'hui.</li>
            <li class='mb-2'><strong>💰 Encaissements :</strong> {m['montant_encaisse_mois']} DT encaissés ce mois (patients).</li>
            <li class='mb-2'><strong>🏥 CNAM en attente :</strong> {m['impayes_montant']} DT à recouvrer ({len(factures_cnam_attente)} factures).</li>
            <li class='mb-2'><strong>👤 Nouveaux patients :</strong> {m['patients_crees_mois']} dossiers créés ce mois.</li>
            <li class='mb-2'><strong>⚠️ Dossiers incomplets :</strong> {m['dossiers_incomplets_count']} patients avec dossier à compléter ({m['taux_dossiers_incomplets']}%).</li>
            <li class='mb-2'><strong>❌ RDV annulés :</strong> {m['rdv_annules']} annulations ce mois ({taux_annul}% du total).</li>
        </ul>
        """
        m['_insights_html'] = html

        return m

    # ---------------------------------------------------------
    # 2. MOTEUR IA LOCAL (CALCULS & LOGIQUE MÉDICALE)
    # ---------------------------------------------------------

    def _calculate_health_index(self, metrics):
        """Calcule un indice de santé du cabinet de 0 à 100 basé sur des indicateurs pondérés."""
        score = 100
        
        # Pénalité Baisse d'activité (Consultations)
        if metrics['tendance_consults'] < 0:
            penalite = min(20, abs(metrics['tendance_consults']) * 2)
            score -= penalite
            
        # Pénalité Financière (Impayés)
        if metrics['nb_factures_impayees'] > 0:
            penalite_fin = min(30, metrics['nb_factures_impayees'] * 5)
            score -= penalite_fin
            
        # Pénalité Médicale (Alertes critiques récurrentes)
        if metrics.get('nb_alertes_critiques', 0) > 2:
            score -= 10
            
        metrics['health_score'] = max(0, score)
        
        # Explication du score
        if score >= 80:
            metrics['health_context'] = "Excellente activité et maîtrise des risques médicaux."
        elif score >= 60:
            metrics['health_context'] = "Activité stable, quelques points financiers ou cliniques à surveiller."
        elif score >= 40:
            metrics['health_context'] = "À surveiller : baisse d'activité ou risques médicaux identifiés."
        else:
            metrics['health_context'] = "Critique : trésorerie en danger ou alertes médicales urgentes."

    def _detect_anomalies(self, metrics):
        """Détecte les anomalies médicales et financières."""
        anomalies = []
        if metrics['tendance_consults'] <= -5:
            anomalies.append(f"Chute de {-metrics['tendance_consults']} consultations ce mois.")
        if metrics.get('nb_alertes_allergies', 0) > 5:
            anomalies.append(f"Pic d'alertes allergies ({metrics['nb_alertes_allergies']} détectées par l'IA).")
        if metrics['nb_factures_impayees'] >= 5:
            anomalies.append(f"Hausse des impayés avec {metrics['nb_factures_impayees']} factures en souffrance.")
            
        metrics['ai_anomalies'] = " / ".join(anomalies) if anomalies else "Aucune anomalie critique détectée par les algorithmes locaux."

    def _compute_forecasts(self, metrics):
        """Estime la fréquentation M+1 via une moyenne pondérée de l'historique."""
        historique = metrics.get('us35_data', [])
        if len(historique) >= 3:
            tendance = (historique[-1] - historique[-3]) / 3
            forecast = int(historique[-1] + tendance)
            confiance = "Faible" if abs(tendance) > 20 else "Élevée"
            metrics['ai_forecasts'] = f"{forecast} consultations prévues. (Confiance: {confiance})"
        else:
            metrics['ai_forecasts'] = "Données historiques insuffisantes pour prévision M+1."

    def _generate_recommendations(self, metrics):
        """Génère des actions concrètes basées sur l'analyse."""
        recos = []
        if metrics.get('nb_alertes_allergies', 0) > 0:
            recos.append("Vérifiez les prescriptions pour les patients à risque d'allergie.")
        if metrics['nb_factures_impayees'] > 0:
            recos.append("Priorisez le recouvrement des impayés patients.")
        if not recos:
            recos.append("Maintenez vos protocoles de suivi actuels, aucun risque majeur identifié.")
            
        metrics['ai_recommendations'] = " ".join(recos)

    # 3. INTÉGRATION IA LOCAL
    # ---------------------------------------------------------

    def _call_ia_api(self, metrics, is_medecin):
        """Lit l'analyse Ollama stockée si elle correspond aux données actuelles, sinon bascule sur l'analyse locale."""
        if not is_medecin:
            metrics['is_fallback'] = False
            html = metrics.pop('_insights_html', "<p class='text-muted'>Aucune donnée disponible.</p>")
            return {'html': html, 'stats': metrics}
            
        import hashlib
        from markupsafe import escape

        ir_config_param = self.env['ir.config_parameter'].sudo()
        current_hash = self._compute_metrics_hash(metrics)
        stored_hash = ir_config_param.get_param('cabinet_medical.ai_analysis_hash')
        stored_text = ir_config_param.get_param('cabinet_medical.ai_analysis_text')
        stored_date = ir_config_param.get_param('cabinet_medical.ai_analysis_date')
        stored_duration = ir_config_param.get_param('cabinet_medical.ai_analysis_duration')
        stored_model = ir_config_param.get_param('cabinet_medical.ai_analysis_model', 'qwen2.5:1.5b')

        # Condition stricte : Le texte Ollama n'est affiché QUE si le hash correspond exactement aux chiffres actuels
        if stored_text and stored_hash == current_hash:
            metrics['is_fallback'] = False
            metrics['ai_recommendations'] = stored_text
            metrics['ai_clinical'] = f"Analyse générée par Ollama ({stored_model}) le {stored_date}, en {stored_duration} s."
            escaped_text = escape(stored_text)
            html = f"""
            <div class='alert alert-success border-0 rounded-3 mb-0' style='background: #f0fdf4; border-left: 4px solid #16a34a !important;'>
                <p class='mb-2 fw-bold text-success'><i class='fa fa-shield me-2'></i>Analyse générée par Ollama ({stored_model}) le {stored_date}, en {stored_duration} s :</p>
                <p class='mb-0 text-dark' style='font-size: 13.5px; line-height: 1.5; white-space: pre-line;'>{escaped_text}</p>
                <p class='mb-0 mt-2 text-muted fst-italic' style='font-size: 11.5px;'>Texte généré par une IA locale, à vérifier par le médecin.</p>
            </div>
            """
            return {'html': html, 'stats': metrics}

        _logger.info("Chiffres du cabinet modifiés ou analyse non encore générée par l'IA (actuel: %s, stocké: %s). Passage à l'analyse locale.", current_hash, stored_hash)
        return self._generate_local_fallback(metrics, is_medecin)

    def _compute_metrics_hash(self, metrics):
        """Calcule un hash SHA-256 déterministe des chiffres réels du cabinet."""
        import hashlib
        sig = (
            f"consults={metrics.get('consults_ce_mois', 0)}|"
            f"alertes={metrics.get('nb_alertes_allergies', 0)}|"
            f"factures={metrics.get('nb_factures_impayees', 0)}|"
            f"impayes={metrics.get('impayes_patients', 0)}|"
            f"patients={metrics.get('patients_total', 0)}|"
            f"consults_prec={metrics.get('consults_mois_dernier', 0)}|"
            f"fact_mois={metrics.get('factures_ce_mois', 0)}|"
            f"fact_prec={metrics.get('factures_mois_dernier', 0)}"
        )
        return hashlib.sha256(sig.encode('utf-8')).hexdigest()[:16]

    @api.model
    def _generate_ai_analysis(self):
        """Génère l'analyse réelle via Ollama et enregistre texte, hash, date, modèle et durée."""
        import requests
        import time
        from datetime import datetime
        import pytz

        ir_config_param = self.env['ir.config_parameter'].sudo()
        url = ir_config_param.get_param('cabinet_medical.ollama_url', 'http://ollama:11434/api/generate') or 'http://ollama:11434/api/generate'
        model = ir_config_param.get_param('cabinet_medical.ollama_model', 'qwen2.5:1.5b') or 'qwen2.5:1.5b'

        # 1. Verrou anti-concurrence (5 minutes max)
        lock_ts = float(ir_config_param.get_param('cabinet_medical.ai_generation_lock', '0') or '0')
        now_ts = time.time()
        if lock_ts and (now_ts - lock_ts < 300):
            _logger.warning("Génération IA déjà en cours (verrou actif depuis %.1f s).", now_ts - lock_ts)
            return {'status': 'locked', 'reason': 'generation_in_progress'}

        # 2. Calcul des métriques globales réelles du cabinet
        today = fields.Date.context_today(self)
        first_day_month = today.replace(day=1)
        first_day_last_month = (first_day_month - relativedelta(months=1))
        last_day_last_month = first_day_month - timedelta(days=1)
        metrics = self._collect_base_metrics(today, first_day_month, first_day_last_month, last_day_last_month)
        med_metrics = self._collect_medical_metrics(first_day_month)
        metrics.update(med_metrics)
        current_hash = self._compute_metrics_hash(metrics)

        # 3. Sauter si le hash actuel est déjà identique au hash stocké
        stored_hash = ir_config_param.get_param('cabinet_medical.ai_analysis_hash')
        stored_text = ir_config_param.get_param('cabinet_medical.ai_analysis_text')
        if stored_text and stored_hash == current_hash:
            _logger.info("Cron/Génération IA : Chiffres inchangés (hash %s identique). Appel Ollama ignoré.", current_hash)
            return {'status': 'skipped', 'reason': 'hash_unchanged'}

        # Poser le verrou
        ir_config_param.set_param('cabinet_medical.ai_generation_lock', str(now_ts))

        consults = metrics.get('consults_ce_mois', 0)
        consults_prec = metrics.get('consults_mois_dernier', 0)
        factures = metrics.get('factures_ce_mois', 0)
        factures_prec = metrics.get('factures_mois_dernier', 0)
        alertes = metrics.get('nb_alertes_allergies', 0)
        impayees = metrics.get('nb_factures_impayees', 0)
        montant_imp = metrics.get('impayes_patients', 0)
        patients_tot = metrics.get('patients_total', 0)

        medecin_nom = "le médecin"
        if self.env.user and self.env.user.name and self.env.user.id != 1:
            medecin_nom = self.env.user.name

        prompt = (
            f"Rédige une analyse concise pour {medecin_nom}, médecin du cabinet.\n"
            f"Règles strictes :\n"
            f"- Utilise uniquement les chiffres fournis. N'invente aucun chiffre.\n"
            f"- Ne parle d'aucune tendance ou comparaison absente des données.\n"
            f"- Format : 3 phrases courtes, puis une ligne 'Recommandations :' suivie de 2 recommandations numérotées.\n"
            f"- N'utilise aucun markdown, aucun astérisque, aucun titre.\n"
            f"- Réponds en français.\n\n"
            f"Exemple (chiffres fictifs) :\n"
            f"Données : ce mois : 40 consultations, mois précédent : 55 ; factures : 38 ce mois, 50 le mois précédent ; 1 alerte allergie ; 12 factures impayées (300 DT) ; 200 patients.\n"
            f"Réponse :\n"
            f"Le cabinet compte 40 consultations ce mois contre 55 sur tout le mois précédent. Une alerte d'allergie médicamenteuse a été bloquée avant prescription. Douze factures restent impayées pour un montant total de 300 DT.\n"
            f"Recommandations :\n"
            f"1. Relancer les 12 factures impayées.\n"
            f"2. Examiner le dossier lié à l'alerte d'allergie.\n\n"
            f"Données réelles du cabinet :\n"
            f"Données : ce mois : {consults} consultations, mois précédent : {consults_prec} ; factures : {factures} ce mois, {factures_prec} le mois précédent ; {alertes} alerte(s) allergie bloquée(s) ; {impayees} factures impayées ({montant_imp} DT) ; {patients_tot} patients.\n"
            f"Réponse :\n"
        )

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "60m",
            "options": {
                "num_predict": 200,
                "num_ctx": 2048,
                "temperature": 0.2,
            }
        }

        t0 = time.time()
        try:
            response = requests.post(url, json=payload, timeout=300)
            duration = round(time.time() - t0, 1)
            if response.status_code != 200:
                _logger.error("Ollama a répondu HTTP %s : %s", response.status_code, response.text[:200])
                return {'status': 'error', 'reason': f'http_{response.status_code}'}

            data = response.json()
            done_reason = data.get('done_reason')
            result_text = self._clean_ai_text(data.get('response', ''), truncated=(done_reason == 'length'))

            if len(result_text) < 40:
                _logger.warning("Réponse Ollama refusée (vide ou < 40 caractères) : %r", result_text)
                return {'status': 'rejected', 'reason': 'too_short', 'text': result_text}

            tunis_tz = pytz.timezone('Africa/Tunis')
            now_tunis = datetime.now(pytz.utc).astimezone(tunis_tz)
            now_str = now_tunis.strftime('%d/%m/%Y à %H:%M')

            ir_config_param.set_param('cabinet_medical.ai_analysis_text', result_text)
            ir_config_param.set_param('cabinet_medical.ai_analysis_date', now_str)
            ir_config_param.set_param('cabinet_medical.ai_analysis_hash', current_hash)
            ir_config_param.set_param('cabinet_medical.ai_analysis_duration', str(duration))
            ir_config_param.set_param('cabinet_medical.ai_analysis_model', model)
            _logger.info("Analyse Ollama générée en %ss (done_reason=%s, eval_count=%s) pour le hash %s",
                         duration, done_reason, data.get('eval_count'), current_hash)
            return {'status': 'success', 'duration': duration, 'text': result_text,
                    'done_reason': done_reason, 'eval_count': data.get('eval_count'),
                    'eval_duration': data.get('eval_duration'), 'load_duration': data.get('load_duration')}
        except Exception as e:
            _logger.error("Erreur lors de l'appel Ollama : %s", e)
            return {'status': 'error', 'reason': str(e)}
        finally:
            ir_config_param.set_param('cabinet_medical.ai_generation_lock', '0')

    @api.model
    def _warmup_ollama(self):
        """Envoie à Ollama un prompt minimal ('ok') avec keep_alive 60m pour précharger le modèle en mémoire."""
        import requests
        import time
        ir_config_param = self.env['ir.config_parameter'].sudo()
        url = ir_config_param.get_param('cabinet_medical.ollama_url', 'http://ollama:11434/api/generate') or 'http://ollama:11434/api/generate'
        model = ir_config_param.get_param('cabinet_medical.ollama_model', 'qwen2.5:1.5b') or 'qwen2.5:1.5b'
        payload = {
            "model": model,
            "prompt": "ok",
            "keep_alive": "60m",
            "options": {"num_predict": 1}
        }
        t0 = time.time()
        try:
            resp = requests.post(url, json=payload, timeout=300)
            duration = round(time.time() - t0, 1)
            if resp.status_code == 200:
                _logger.info("Préchauffage Ollama réussi en %ss (modèle %s maintenu 60m).", duration, model)
                return {'status': 'success', 'duration': duration, 'model': model}
            _logger.warning("Préchauffage Ollama code HTTP %s", resp.status_code)
            return {'status': 'error', 'reason': f'http_{resp.status_code}'}
        except Exception as e:
            _logger.warning("Échec du préchauffage Ollama : %s", e)
            return {'status': 'error', 'reason': str(e)}

    @api.model
    def _clean_ai_text(self, text, truncated=False):
        """Supprime le markdown (**, #, titres) et coupe à la dernière phrase complète si la réponse est tronquée."""
        import re
        if not text:
            return ''
        text = text.replace('**', '').replace('__', '')
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Ligne de titre markdown (#, ##, ...) : supprimée
            if stripped.startswith('#'):
                continue
            # Ligne de titre sans ponctuation finale terminée par ':' (sauf la ligne 'Recommandations :')
            if stripped.endswith(':') and not stripped.lower().startswith('recommandation') and len(stripped) < 60:
                continue
            stripped = stripped.replace('#', '').strip()
            if stripped.startswith(('- ', '* ')):
                stripped = stripped[2:].strip()
            lines.append(stripped)
        text = '\n'.join(lines).strip()

        # Si tronqué en plein milieu de phrase (done_reason == 'length' ou manque de ponctuation terminale)
        clean_stripped = text.rstrip()
        missing_punct = bool(clean_stripped and clean_stripped[-1] not in ('.', '!', '?'))
        if truncated or missing_punct:
            # Couper proprement après la dernière fin de phrase complète
            # (?<!\d) : ne pas considérer « 1. » / « 2. » comme une fin de phrase
            matches = list(re.finditer(r'(?<!\d)[.!?](?=\s|$)', text))
            if matches:
                text = text[:matches[-1].end()].strip()
        return text

    @api.model
    def action_trigger_ai_regeneration(self):
        """Action RPC appelée depuis le bouton pour lancer la génération en arrière-plan."""
        import threading
        import time
        ir_config_param = self.env['ir.config_parameter'].sudo()
        lock_ts = float(ir_config_param.get_param('cabinet_medical.ai_generation_lock', '0') or '0')
        now_ts = time.time()
        if lock_ts and (now_ts - lock_ts < 300):
            return {'status': 'locked'}

        def worker():
            with self.pool.cursor() as new_cr:
                new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                new_env['cabinet.dashboard.ai']._generate_ai_analysis()
                new_cr.commit()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return {'status': 'started'}

    @api.model
    def check_ai_status(self):
        """Vérifie l'état de la génération en cours pour le polling JS."""
        import time
        ir_config_param = self.env['ir.config_parameter'].sudo()
        lock_ts = float(ir_config_param.get_param('cabinet_medical.ai_generation_lock', '0') or '0')
        now_ts = time.time()
        is_generating = bool(lock_ts and (now_ts - lock_ts < 300))
        return {'is_generating': is_generating}

    def _generate_local_fallback(self, metrics, is_medecin):
        """Moteur local heuristique lorsque l'IA n'a pas encore calculé le hash actuel."""
        _logger.warning("Affichage de l'analyse locale heuristique.")
        metrics['is_fallback'] = True
        metrics['ai_us35'] = f"Consultations {'en hausse' if metrics['tendance_consults']>0 else 'en baisse'} ({metrics['tendance_consults']} RDV)."
        metrics['ai_us36'] = "Répartition stable."
        metrics['ai_us37'] = "Créances en attente à suivre."
        metrics['ai_us39'] = "Maintien de la patientèle."
        
        html = f"""
        <div class='alert alert-light border rounded-3 mb-0' style='background: #f8fafc; border-left: 4px solid #64748b !important;'>
            <p class='mb-2 fw-bold text-secondary'><i class='fa fa-calculator me-2'></i>Analyse locale (chiffres modifiés ou en attente d'actualisation IA) :</p>
            <ul class='list-unstyled mb-0 small text-muted'>
                <li class='mb-1'><strong>Activité :</strong> {metrics.get('consults_ce_mois', 0)} consultations ce mois. {metrics.get('ai_us35', '')}</li>
                <li class='mb-1'><strong>Sécurité clinique :</strong> {metrics.get('nb_alertes_allergies', 0)} alertes allergies interceptées.</li>
                <li class='mb-1'><strong>Impayés :</strong> {metrics.get('nb_factures_impayees', 0)} factures à recouvrer ({metrics.get('impayes_patients', 0)} DT).</li>
            </ul>
        </div>
        """
        return {'html': html, 'stats': metrics}
