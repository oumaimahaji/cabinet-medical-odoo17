import json
import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import Counter
from typing import Any, Dict
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class DashboardAI(models.AbstractModel):
    _name = 'cabinet.dashboard.ai'
    _description = 'Assistant IA du Tableau de Bord'

    @api.model
    def get_ai_insights(self):
        """
        Méthode principale d'orchestration de l'Assistant IA.
        Appelle les méthodes modulaires pour collecter les données,
        calcule les scores et anomalies, et sollicite l'IA Claude.
        """
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
            
            return self._call_claude_api(metrics, is_medecin)
        else:
            # Sécrétaire
            metrics = self._collect_secretaire_metrics(today, first_day_month, first_day_last_month, last_day_last_month)
            return self._call_claude_api(metrics, False)

    # ---------------------------------------------------------
    # 1. COLLECTE DE DONNÉES (MODULARISÉE POUR LA SOUTENANCE)
    # ---------------------------------------------------------

    def _collect_base_metrics(self, today, first_day_month, first_day_last_month, last_day_last_month):
        """Collecte les indicateurs d'activité globaux et financiers (Médecin)."""
        metrics: dict[str, Any] = {'isMedecin': True}
        
        # Consultations
        metrics['consults_jour'] = self.env['cabinet.consultation'].search_count([('date_consultation', '=', today)])
        metrics['consults_ce_mois'] = self.env['cabinet.consultation'].search_count([('date_consultation', '>=', first_day_month)])
        metrics['consults_mois_dernier'] = self.env['cabinet.consultation'].search_count([
            ('date_consultation', '>=', first_day_last_month),
            ('date_consultation', '<=', last_day_last_month)
        ])
        metrics['tendance_consults'] = metrics['consults_ce_mois'] - metrics['consults_mois_dernier']
        
        # Impayés
        factures_impayees = self.env['cabinet.facture'].search([('state', '=', 'validated'), ('reste_a_charge_final', '>', 0)])
        metrics['impayes_patients'] = round(sum(f.reste_a_charge_final for f in factures_impayees), 3)
        metrics['nb_factures_impayees'] = len(factures_impayees)
        
        # Profils Patients
        patients_du_mois = self.env['cabinet.consultation'].search([('date_consultation', '>=', first_day_month)]).mapped('patient_id')
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
        ordonnances = self.env['cabinet.prescription'].search(
            [('date_prescription', '>=', fenetre_30j)]
        )
        
        nb_alertes = 0
        nb_alertes_critiques = 0
        meds_prescrits = []
        
        for ordo in ordonnances:
            # BUG FIX #1 : On utilise le champ STOCKÉ ia_statut plutôt qu'une recherche
            # textuelle dans ia_message (fragile car le message peut avoir des variantes).
            # ia_statut == 'allergy_risk' est positionné par _verify_ia_in_memory() et
            # persisté via action_verifier_ia() -> write().
            if ordo.ia_statut == 'allergy_risk':
                nb_alertes += 1
                # Alerte critique : score ≥ 90% OU mot-clé 'critique' dans le message IA
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
        consults = self.env['cabinet.consultation'].search([('date_consultation', '>=', first_day_month)])
        avec_ordo = sum(1 for c in consults if c.prescription_ids)
        sans_ordo = len(consults) - avec_ordo
        med_metrics['consults_avec_ordo'] = avec_ordo
        med_metrics['consults_sans_ordo'] = sans_ordo
        
        # Patients à risque (ayant des allergies)
        patients = self.env['cabinet.patient'].search([('allergies', '!=', False)])
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

    # ---------------------------------------------------------
    # 3. INTÉGRATION API CLAUDE
    # ---------------------------------------------------------

    def _call_claude_api(self, metrics, is_medecin):
        """Prépare le prompt, appelle Claude et gère le fallback si l'API est indisponible."""
        if not is_medecin:
            # BUG FIX #1 (insights secrétaire) : on retourne le HTML pré-généré
            # par _collect_secretaire_metrics() au lieu du message "en maintenance".
            html = metrics.pop('_insights_html', "<p class='text-muted'>Aucune donnée disponible.</p>")
            return {'html': html, 'stats': metrics}
            
        prompt = f"""En tant qu'Assistant IA Clinique, analyse les données du cabinet médical. Toutes tes analyses doivent être justifiées par ces chiffres.
        
Données Médicales et IA :
- Alertes Allergies IA détectées ce mois : {metrics.get('nb_alertes_allergies', 0)} (dont {metrics.get('nb_alertes_critiques', 0)} critiques)
- Patients avec allergies dans la base : {metrics.get('patients_allergiques', 0)}
- Top Médicaments prescrits : {metrics.get('top_medicaments', 'N/A')}
- Ratio de consultations avec/sans ordonnance : {metrics.get('consults_avec_ordo', 0)} / {metrics.get('consults_sans_ordo', 0)}

Données d'Activité :
- Consultations ce mois : {metrics['consults_ce_mois']} (vs {metrics['consults_mois_dernier']} mois dernier)
- Historique 6 mois consultations : {metrics.get('us35_data')}
- Score de Santé (pré-calculé) : {metrics['health_score']}/100

Tu DOIS retourner un objet JSON strict avec EXACTEMENT ces clés (AUCUN AUTRE TEXTE) :
{{
    "top_insights_html": "HTML <ul><li> (sans classes spécifiques, mets en valeur l'IA médicale et justifie tout avec les données fournies).",
    "global_health_score": un entier de 0 à 100 reflétant la santé du cabinet,
    "detected_anomalies": "Phrase listant les anomalies justifiées (ex: Baisse de X consultations).",
    "recommendations": "Actions cliniques ou de gestion priorisées.",
    "forecasts": "Estimation argumentée des consultations M+1 avec mention de la Confiance (Faible/Moyen/Élevé).",
    "us35_comment": "Analyse de la courbe des consultations (Max 1 ligne).",
    "us36_comment": "Analyse de la répartition du CA (Max 1 ligne).",
    "us37_comment": "Analyse des créances CNAM (Max 1 ligne).",
    "us39_comment": "Analyse de la répartition patients (Max 1 ligne)."
}}
"""
        import os
        api_key = self.env['ir.config_parameter'].sudo().get_param('cabinet_medical.claude_api_key') or os.environ.get('CLAUDE_API_KEY')
        
        # Si pas de clé Claude configurée -> bascule vers Ollama local
        if not api_key:
            return self._call_ollama_fallback(metrics, prompt, is_medecin)

        try:
            import requests
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            payload = {"model": "claude-haiku-4-5-20251001", "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}
            
            response = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=12)
            if response.status_code == 200:
                result = response.json()
                json_str = result.get('content', [{}])[0].get('text', '')
                if "```json" in json_str: json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str: json_str = json_str.split("```")[1].split("```")[0]
                
                ai_data = json.loads(json_str.strip())
                metrics['health_score'] = ai_data.get('global_health_score', metrics['health_score'])
                metrics['ai_anomalies'] = ai_data.get('detected_anomalies', metrics['ai_anomalies'])
                metrics['ai_recommendations'] = ai_data.get('recommendations', metrics['ai_recommendations'])
                metrics['ai_forecasts'] = ai_data.get('forecasts', metrics['ai_forecasts'])
                metrics['ai_us35'] = ai_data.get('us35_comment', '')
                metrics['ai_us36'] = ai_data.get('us36_comment', '')
                metrics['ai_us37'] = ai_data.get('us37_comment', '')
                metrics['ai_us39'] = ai_data.get('us39_comment', '')
                return {'html': ai_data.get('top_insights_html', ''), 'stats': metrics}
            else:
                _logger.warning(f"Claude API Error (status {response.status_code}): {response.text}. Bascule sur Ollama local.")
                return self._call_ollama_fallback(metrics, prompt, is_medecin)
                
        except Exception as e:
            _logger.warning(f"Claude API Exception: {e}. Bascule sur Ollama local.")
            return self._call_ollama_fallback(metrics, prompt, is_medecin)

    def _call_ollama_fallback(self, metrics, prompt, is_medecin):
        """Secours Ollama local : appelle le LLM local (phi3 ou tinyllama) si Claude n'est pas disponible."""
        import requests
        ir_config_param = self.env['ir.config_parameter'].sudo()
        url = ir_config_param.get_param('cabinet_medical.ollama_url', 'http://ollama:11434/api/generate')
        model = ir_config_param.get_param('cabinet_medical.ollama_model', 'tinyllama')

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 800
                }
            }
            response = requests.post(url, json=payload, timeout=(2.0, 30.0))
            if response.status_code == 200:
                result = response.json()
                raw_text = result.get('response', '').strip()
                json_str = raw_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]
                try:
                    ai_data = json.loads(json_str.strip())
                    metrics['health_score'] = ai_data.get('global_health_score', metrics['health_score'])
                    metrics['ai_anomalies'] = ai_data.get('detected_anomalies', metrics['ai_anomalies'])
                    metrics['ai_recommendations'] = ai_data.get('recommendations', metrics['ai_recommendations'])
                    metrics['ai_forecasts'] = ai_data.get('forecasts', metrics['ai_forecasts'])
                    metrics['ai_us35'] = ai_data.get('us35_comment', '')
                    metrics['ai_us36'] = ai_data.get('us36_comment', '')
                    metrics['ai_us37'] = ai_data.get('us37_comment', '')
                    metrics['ai_us39'] = ai_data.get('us39_comment', '')
                    html = ai_data.get('top_insights_html', f"<p>🤖 <em>[Secours LLM {model}]</em> {raw_text[:250]}</p>")
                    return {'html': html, 'stats': metrics}
                except Exception:
                    html = f"""
                    <ul class='list-unstyled mb-0'>
                        <li class='mb-2'><strong>🤖 Assistant LLM Local ({model}) :</strong> {raw_text[:300]}</li>
                        <li class='mb-2'><strong>🩺 Statut Médical :</strong> Données analysées localement en mode sécurisé.</li>
                    </ul>
                    """
                    return {'html': html, 'stats': metrics}
            else:
                _logger.warning(f"Ollama API Error status {response.status_code}: {response.text}")
                return self._generate_local_fallback(metrics, is_medecin)
        except Exception as e:
            _logger.info(f"Ollama local non joignable ({e}), passage au moteur local heuristique.")
            return self._generate_local_fallback(metrics, is_medecin)

    def _generate_local_fallback(self, metrics, is_medecin):
        """Moteur local générant des analyses basiques justifiées en cas d'absence de Claude."""
        metrics['ai_us35'] = f"Consultations {'en hausse' if metrics['tendance_consults']>0 else 'en baisse'} ({metrics['tendance_consults']} RDV)."
        metrics['ai_us36'] = "Répartition stable."
        metrics['ai_us37'] = "Créances en attente à suivre."
        metrics['ai_us39'] = "Maintien de la patientèle."
        
        html = f"""
        <ul class='list-unstyled mb-0'>
            <li class='mb-2'><strong>🩺 Intelligence Clinique :</strong> {metrics.get('nb_alertes_allergies',0)} alertes allergies bloquées par l'IA ce mois-ci.</li>
            <li class='mb-2'><strong>💊 Prescription :</strong> Médicaments fréquents: {metrics.get('top_medicaments','Aucun')}.</li>
            <li class='mb-2'><strong>⚠️ Statut Santé :</strong> Score calculé localement à {metrics['health_score']}/100. {metrics.get('health_context','')}</li>
        </ul>
        """
        return {'html': html, 'stats': metrics}
