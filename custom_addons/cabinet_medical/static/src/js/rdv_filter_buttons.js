/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { FormController } from "@web/views/form/form_controller";

console.log("RDV FILTER JS LOADED - version 17.0.1.0.2");

patch(FormViewDialog.prototype, {
    setup() {
        super.setup();
        console.log("FormViewDialog setup called. Props:", this.props);
    }
});

/**
 * Configure la fonction de filtre pour un contrôleur (Liste ou Calendrier)
 */
function setupRdvFilter(component) {
    component._rdvActiveFilter = "today"; // default

    const updateRdvButtons = function (filterKey) {
        const buttons = {
            "today": document.getElementById("rdv-btn-today"),
            "upcoming": document.getElementById("rdv-btn-upcoming"),
            "present": document.getElementById("rdv-btn-present"),
            "en_attente": document.getElementById("rdv-btn-en_attente"),
            "en_consultation": document.getElementById("rdv-btn-en_consultation"),
            "termine": document.getElementById("rdv-btn-termine")
        };

        const stylesActive = {
            "today": "background: #0284c7; color: white; font-weight: 700; border-radius: 6px; padding: 7px 16px; border: none; cursor: pointer; font-size: 13px; box-shadow:0 2px 6px rgba(0,0,0,0.15); transition: all 0.2s;",
            "upcoming": "background: #8e44ad; color: white; font-weight: 700; border-radius: 6px; padding: 7px 16px; border: none; cursor: pointer; font-size: 13px; box-shadow:0 2px 6px rgba(0,0,0,0.15); transition: all 0.2s;",
            "present": "background: #27ae60; color: white; font-weight: 700; border-radius: 6px; padding: 7px 16px; border: none; cursor: pointer; font-size: 13px; box-shadow:0 2px 6px rgba(0,0,0,0.15); transition: all 0.2s;",
            "en_attente": "background: #e67e22; color: white; font-weight: 700; border-radius: 6px; padding: 7px 16px; border: none; cursor: pointer; font-size: 13px; box-shadow:0 2px 6px rgba(0,0,0,0.15); transition: all 0.2s;",
            "en_consultation": "background: #2980b9; color: white; font-weight: 700; border-radius: 6px; padding: 7px 16px; border: none; cursor: pointer; font-size: 13px; box-shadow:0 2px 6px rgba(0,0,0,0.15); transition: all 0.2s;",
            "termine": "background: #7f8c8d; color: white; font-weight: 700; border-radius: 6px; padding: 7px 16px; border: none; cursor: pointer; font-size: 13px; box-shadow:0 2px 6px rgba(0,0,0,0.15); transition: all 0.2s;"
        };

        const styleInactive =
            "background: transparent; color: white; font-weight: 600; border-radius: 6px; padding: 7px 16px; border: none; cursor: pointer; font-size: 13px; transition: all 0.2s;";

        Object.entries(buttons).forEach(([key, btn]) => {
            if (btn) {
                btn.style.cssText = filterKey === key ? (stylesActive[key] || styleInactive) : styleInactive;
            }
        });
    };

    component.rdvSetFilter = function (filterKey) {
        const searchModel = component.env.searchModel;
        if (!searchModel) return;

        // Récupérer tous les items de recherche disponibles
        const items = searchModel.searchItems;

        // Liste de tous les filtres rapides à désactiver d'abord
        const allFilters = [
            "filter_today", "today",
            "filter_upcoming", "upcoming",
            "filter_present", "present",
            "filter_en_attente", "en_attente",
            "filter_en_consultation", "en_consultation",
            "filter_termine", "termine"
        ];

        Object.values(items).forEach((item) => {
            if (allFilters.includes(item.name)) {
                const isActive = searchModel.query.some((q) => q.searchItemId === item.id);
                if (isActive) {
                    searchModel.toggleSearchItem(item.id);
                }
            }
        });

        // Déterminer les noms cibles pour le filtre sélectionné (compatibilité Docteur/Secrétaire)
        let targets = [];
        if (filterKey === "today") targets = ["filter_today", "today"];
        else if (filterKey === "upcoming") targets = ["filter_upcoming", "upcoming"];
        else if (filterKey === "present") targets = ["filter_present", "present"];
        else if (filterKey === "en_attente") targets = ["filter_en_attente", "en_attente"];
        else if (filterKey === "en_consultation") targets = ["filter_en_consultation", "en_consultation"];
        else if (filterKey === "termine") targets = ["filter_termine", "termine"];

        // Activer le filtre sélectionné
        const targetItem = Object.values(items).find((i) => targets.includes(i.name));
        if (targetItem) {
            searchModel.toggleSearchItem(targetItem.id);
        }

        component._rdvActiveFilter = filterKey;
        updateRdvButtons(filterKey);

        if (window._rdvRefreshBanner) {
            window._rdvRefreshBanner();
        }
    };

    // Synchroniser l'état initial des boutons avec le searchModel
    setTimeout(() => {
        const searchModel = component.env.searchModel;
        if (!searchModel) return;
        const items = searchModel.searchItems;
        let activeKey = "today";
        for (const key of ["upcoming", "present", "en_attente", "en_consultation", "termine", "today"]) {
            const targets = key === "today" ? ["filter_today", "today"] :
                            key === "upcoming" ? ["filter_upcoming", "upcoming"] :
                            key === "present" ? ["filter_present", "present"] :
                            key === "en_attente" ? ["filter_en_attente", "en_attente"] :
                            key === "en_consultation" ? ["filter_en_consultation", "en_consultation"] :
                            ["filter_termine", "termine"];
            const item = Object.values(items).find(i => targets.includes(i.name));
            if (item && searchModel.query.some(q => q.searchItemId === item.id)) {
                activeKey = key;
                break;
            }
        }
        updateRdvButtons(activeKey);
    }, 50);

    component.rdvOpenForm = function (dateStr, heureFloat, patientId, rdvId) {
        if (component.env && component.env.services && component.env.services.dialog) {
            let ctx = {
                default_date: dateStr,
                default_heure: heureFloat,
                form_view_initial_mode: 'edit',
                create: true,
                edit: true
            };
            if (patientId && patientId !== 'null') {
                ctx.default_patient_id = parseInt(patientId);
            }
            if (window._isMedecin) {
                ctx.form_view_ref = 'cabinet_medical.view_appointment_form_suivi_medecin';
            } else {
                ctx.form_view_ref = 'cabinet_medical.view_appointment_form_secretaire_edit';
            }

            component.env.services.dialog.add(FormViewDialog, {
                resModel: 'cabinet.rendezvous',
                resId: rdvId || false,
                context: ctx,
                title: rdvId ? 'Détails du rendez-vous' : 'Créer un rendez-vous',
                onRecordSaved: () => {
                    if (window._rdvRefreshBanner) window._rdvRefreshBanner();
                    if (component && component.model && typeof component.model.load === "function") {
                        component.model.load();
                    }
                },
            });
        }
    };
}

/**
 * Configure la fonction de filtre pour le contrôleur Liste des Consultations
 */
function setupConsultationFilter(component) {
    const updateConsultationButtons = function (activeKey) {
        const btnEnCours = document.getElementById("consult-btn-en_cours");
        const btnTerminees = document.getElementById("consult-btn-terminees");

        const styleEnCoursActive = "background: #e67e22; color: white; font-weight: 700; border-radius: 6px; padding: 7px 18px; border: none; cursor: pointer; font-size: 13px; box-shadow:0 2px 6px rgba(0,0,0,0.15); transition: all 0.2s;";
        const styleTermineesActive = "background: #27ae60; color: white; font-weight: 700; border-radius: 6px; padding: 7px 18px; border: none; cursor: pointer; font-size: 13px; box-shadow:0 2px 6px rgba(0,0,0,0.15); transition: all 0.2s;";
        const styleInactive = "background: transparent; color: white; font-weight: 600; border-radius: 6px; padding: 7px 18px; border: none; cursor: pointer; font-size: 13px; transition: all 0.2s;";

        if (btnEnCours) {
            btnEnCours.style.cssText = activeKey === 'en_cours' ? styleEnCoursActive : styleInactive;
        }
        if (btnTerminees) {
            btnTerminees.style.cssText = activeKey === 'terminees' ? styleTermineesActive : styleInactive;
        }
    };

    component.consultationSetFilter = function (filterKey) {
        const searchModel = component.env.searchModel;
        if (!searchModel) return;

        const items = searchModel.searchItems;
        const enCoursItem = Object.values(items).find(i => i.name === 'en_cours');
        const termineesItem = Object.values(items).find(i => i.name === 'terminees');

        if (filterKey === 'en_cours') {
            if (termineesItem && searchModel.query.some(q => q.searchItemId === termineesItem.id)) {
                searchModel.toggleSearchItem(termineesItem.id);
            }
            if (enCoursItem && !searchModel.query.some(q => q.searchItemId === enCoursItem.id)) {
                searchModel.toggleSearchItem(enCoursItem.id);
            }
        } else if (filterKey === 'terminees') {
            if (enCoursItem && searchModel.query.some(q => q.searchItemId === enCoursItem.id)) {
                searchModel.toggleSearchItem(enCoursItem.id);
            }
            if (termineesItem && !searchModel.query.some(q => q.searchItemId === termineesItem.id)) {
                searchModel.toggleSearchItem(termineesItem.id);
            }
        }

        updateConsultationButtons(filterKey);
    };

    // Synchroniser l'état initial des boutons avec le searchModel
    setTimeout(() => {
        const searchModel = component.env.searchModel;
        if (!searchModel) return;
        const items = searchModel.searchItems;
        const termineesItem = Object.values(items).find(i => i.name === 'terminees');
        const isTerminees = termineesItem && searchModel.query.some(q => q.searchItemId === termineesItem.id);
        updateConsultationButtons(isTerminees ? 'terminees' : 'en_cours');
    }, 50);
}

// 1. Patch de la Vue Liste
patch(ListController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel === 'cabinet.rendezvous') {
            setupRdvFilter(this);
            window._activeRdvController = this;
        } else if (this.props.resModel === 'cabinet.consultation') {
            setupConsultationFilter(this);
            window._activeConsultationController = this;
        }
    }
});

// 2. Patch de la Vue Calendrier
patch(CalendarController.prototype, {
    setup() {
        super.setup();
        setupRdvFilter(this);
        // Sauvegarder le contrôleur actif globalement
        window._activeRdvController = this;
    }
});

// 3. Fonction globale appelée par les clics HTML dans le bandeau (main.py / XML)
window._rdvSetFilter = function (filterKey) {
    if (window._activeRdvController && typeof window._activeRdvController.rdvSetFilter === "function") {
        window._activeRdvController.rdvSetFilter(filterKey);
    } else {
        console.warn("Aucun contrôleur de vue actif trouvé pour appliquer le filtre.");
    }
};

window._consultationSetFilter = function (filterKey) {
    if (window._activeConsultationController && typeof window._activeConsultationController.consultationSetFilter === "function") {
        window._activeConsultationController.consultationSetFilter(filterKey);
    } else {
        console.warn("Aucun contrôleur de consultation actif trouvé pour appliquer le filtre.");
    }
};

window._rdvOpenForm = function (dateStr, heureFloat, patientId, rdvId) {
    if (window._activeRdvController && typeof window._activeRdvController.rdvOpenForm === "function") {
        window._activeRdvController.rdvOpenForm(dateStr, heureFloat, patientId, rdvId);
    } else {
        console.warn("Aucun contrôleur de vue actif trouvé pour ouvrir le formulaire.");
    }
};

// ==========================================
// Logique du Calendrier Interactif (Banner & Popup)
// ==========================================

window._calCurrentMonthDate = new Date();
window._calSelectedDate = null;
window._calPatientId = null;

window._rdvInitCalendar = function (patientId, isMedecin) {
    window._calPatientId = patientId || null;
    window._isMedecin = isMedecin || false;

    // Masquer le calendrier natif d'Odoo de façon robuste
    let hideAttempts = 0;
    const hideInterval = setInterval(() => {
        hideAttempts++;
        const app = document.getElementById('cabinet_calendar_app');
        if (app) {
            const container = app.closest('.o_calendar_container');
            if (container) {
                const renderer = container.querySelector('.o_calendar_renderer');
                if (renderer) renderer.style.setProperty('display', 'none', 'important');

                const sidebar = container.querySelector('.o_calendar_sidebar_container');
                if (sidebar) sidebar.style.setProperty('display', 'none', 'important');

                const header = container.querySelector('.o_calendar_header');
                if (header) header.style.setProperty('display', 'none', 'important');
            }
        }
        if (hideAttempts > 10) clearInterval(hideInterval); // Stop trying after 1 second
    }, 100);

    window._rdvRefreshBanner();
};

function getMonthStr(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, '0');
}

window._rdvRefreshBanner = function () {
    // Only refresh if the calendar app is currently rendered in the DOM
    if (!document.getElementById('cabinet_calendar_app')) {
        return;
    }

    let monthStr = getMonthStr(window._calCurrentMonthDate);
    const monthNames = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];

    let labelEl = document.getElementById('current_month_label');
    if (labelEl) labelEl.innerText = monthNames[window._calCurrentMonthDate.getMonth()] + " " + window._calCurrentMonthDate.getFullYear();

    fetch('/cabinet_medical/get_calendar_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {
                month: monthStr,
                selected_date: window._calSelectedDate
            }
        })
    })
        .then(r => r.json())
        .then(res => {
            if (res.result) {
                window.renderMonth(res.result.month_data, window._calCurrentMonthDate);
                if (window._calSelectedDate) {
                    window.renderDay(res.result.day_data, window._calSelectedDate);
                }
            }
        });
};

window.changeMonth = function (delta) {
    window._calCurrentMonthDate.setMonth(window._calCurrentMonthDate.getMonth() + delta);
    window._calSelectedDate = null;

    let dayLabel = document.getElementById('selected_day_label');
    if (dayLabel) dayLabel.innerHTML = "<i class='fa fa-hand-pointer-o'></i> Sélectionnez un jour";

    let daySlots = document.getElementById('day_slots');
    if (daySlots) daySlots.innerHTML = "<div style='color: #666; font-style: italic; font-size: 14px; padding: 10px;'>Cliquez sur un jour du calendrier à gauche pour voir et réserver les créneaux horaires.</div>";

    window._rdvRefreshBanner();
};

window.selectDay = function (dateStr, isClosed) {
    if (isClosed) return;
    window._calSelectedDate = dateStr;
    document.querySelectorAll('.cal-day').forEach(el => {
        el.style.border = '1px solid #e9ecef';
        el.style.boxShadow = 'none';
        el.style.transform = 'translateY(0)';
    });
    const clicked = document.getElementById('day_' + dateStr);
    if (clicked) {
        clicked.style.border = '2px solid #1a3a6e';
        clicked.style.boxShadow = '0 4px 12px rgba(26,58,110,0.15)';
        clicked.style.transform = 'translateY(-2px)';
    }

    window._rdvRefreshBanner();
};

window.renderMonth = function (monthData, dateObj) {
    const grid = document.getElementById('month_grid');
    if (!grid) return;
    grid.innerHTML = '';

    const year = dateObj.getFullYear();
    const month = dateObj.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    let startOffset = firstDay.getDay() - 1;
    if (startOffset === -1) startOffset = 6;

    for (let i = 0; i < startOffset; i++) {
        grid.innerHTML += `<div style="padding: 10px;"></div>`;
    }

    for (let d = 1; d <= lastDay.getDate(); d++) {
        const dStr = year + "-" + String(month + 1).padStart(2, '0') + "-" + String(d).padStart(2, '0');
        const data = monthData[dStr] || { status: 'closed', label: 'Fermé' };

        let bg = '#fff';
        let border = '1px solid #e9ecef';
        let color = '#333';
        let badgeBg = '#e9ecef';
        let badgeColor = '#666';

        if (data.status === 'green') { badgeBg = '#d4edda'; badgeColor = '#155724'; border = '1px solid #c3e6cb'; }
        else if (data.status === 'orange') { badgeBg = '#fff3cd'; badgeColor = '#856404'; border = '1px solid #ffeeba'; }
        else if (data.status === 'red') { badgeBg = '#f8d7da'; badgeColor = '#721c24'; bg = '#fffcfc'; border = '1px solid #f5c6cb'; }
        else if (data.status === 'closed') { bg = '#f8f9fa'; color = '#adb5bd'; badgeBg = 'transparent'; }

        const isSelected = window._calSelectedDate === dStr;
        if (isSelected) {
            border = '2px solid #1a3a6e';
        }

        const cursor = data.status === 'closed' ? 'not-allowed' : 'pointer';
        const hoverStyle = data.status !== 'closed' && !isSelected ? "onmouseover=\"this.style.boxShadow='0 4px 8px rgba(0,0,0,0.05)'; this.style.transform='translateY(-1px)'\" onmouseout=\"this.style.boxShadow='none'; this.style.transform='translateY(0)'\"" : '';

        grid.innerHTML += `
            <div id="day_${dStr}" class="cal-day" onclick="window.selectDay('${dStr}', ${data.status === 'closed'})" ${hoverStyle}
                 style="border: ${border}; border-radius: 8px; padding: 8px 4px; background: ${bg}; cursor: ${cursor}; text-align: center; transition: all 0.2s; min-height: 55px; display: flex; flex-direction: column; justify-content: space-between; align-items: center;">
                <div style="font-size: 15px; font-weight: 700; color: ${color};">${d}</div>
                ${data.status !== 'closed' ? `<div style="font-size: 10px; margin-top: 4px; padding: 3px 4px; border-radius: 8px; background: ${badgeBg}; color: ${badgeColor}; font-weight: 600; white-space: normal; line-height: 1.1; text-align: center; max-width: 95%;">${data.label}</div>` : `<div style="font-size: 11px; margin-top: 4px; color: #adb5bd; font-weight: 600;">Fermé</div>`}
            </div>
        `;
    }
};

window.renderDay = function (dayData, dateStr) {
    const parts = dateStr.split('-');
    let dayLabel = document.getElementById('selected_day_label');
    if (dayLabel) dayLabel.innerHTML = "<i class='fa fa-clock-o'></i> Créneaux du " + parts[2] + "/" + parts[1] + "/" + parts[0];

    const container = document.getElementById('day_slots');
    if (!container) return;
    container.innerHTML = '';

    if (!dayData || dayData.length === 0) {
        container.innerHTML = "<div style='color: #666; font-style: italic; font-size: 14px; padding: 10px;'>Aucun créneau configuré ce jour.</div>";
        return;
    }

    dayData.forEach(slot => {
        if (slot.is_free) {
            let pid = window._calPatientId ? window._calPatientId : 'null';
            container.innerHTML += `
                <div onclick="window._rdvOpenForm('${dateStr}', ${slot.heure}, ${pid})"
                     style="background: white; border: 2px solid #28a745; color: #28a745; padding: 12px; border-radius: 8px; cursor: pointer; text-align: center; transition: all 0.2s; box-shadow: 0 2px 4px rgba(40,167,69,0.1);"
                     onmouseover="this.style.background='#28a745'; this.style.color='white'; this.style.transform='scale(1.03)'" 
                     onmouseout="this.style.background='white'; this.style.color='#28a745'; this.style.transform='scale(1)'">
                    <div style="font-weight: 800; font-size: 16px;">${slot.label}</div>
                    <div style="font-size: 12px; margin-top: 4px; font-weight: 600;"><i class="fa fa-check-circle"></i> Libre</div>
                </div>
            `;
        } else {
            // Slot occupé
            let bg = "#e9ecef";
            let border = "#ced4da";
            let icon = "fa-user";
            let stateLabel = "Occupé";
            let color = "#495057";

            if (slot.state === 'en_attente') {
                bg = "#fff3cd"; border = "#ffeeba"; icon = "fa-clock-o"; stateLabel = "En attente"; color = "#856404";
            } else if (slot.state === 'present') {
                bg = "#d4edda"; border = "#c3e6cb"; icon = "fa-check-circle"; stateLabel = "Présent"; color = "#155724";
            } else if (slot.state === 'en_consultation') {
                bg = "#cce5ff"; border = "#b8daff"; icon = "fa-stethoscope"; stateLabel = "En consultation"; color = "#004085";
            } else if (slot.state === 'termine') {
                bg = "#e2e3e5"; border = "#d6d8db"; icon = "fa-check-double"; stateLabel = "Terminé"; color = "#383d41";
            }

            let urgenceBadge = slot.is_urgence ? '<div style="position: absolute; top: -5px; right: -5px; background: red; color: white; font-size: 10px; padding: 2px 6px; border-radius: 10px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">Urgence</div>' : '';

            container.innerHTML += `
                <div onclick="window._rdvOpenForm('${dateStr}', ${slot.heure}, null, ${slot.rdv_id})"
                     style="background: ${bg}; border: 1px solid ${border}; color: ${color}; padding: 12px; border-radius: 8px; cursor: pointer; text-align: center; opacity: 0.95; position: relative;"
                     onmouseover="this.style.opacity='1'; this.style.boxShadow='0 2px 6px rgba(0,0,0,0.1)'" 
                     onmouseout="this.style.opacity='0.95'; this.style.boxShadow='none'">
                    <div style="font-weight: 800; font-size: 16px;">${slot.label}</div>
                    <div style="font-size: 11px; margin-top: 4px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${slot.patient_name}"><i class="fa ${icon}"></i> ${slot.patient_name}</div>
                    <div style="font-size: 10px; margin-top: 2px; opacity: 0.8; font-weight: 600;">${stateLabel}</div>
                    ${urgenceBadge}
                </div>
            `;
        }
    });
};

// 4. Patch de FormController pour gérer le bouton Annuler (suppression/unlink) et la sauvegarde
patch(FormController.prototype, {
    async saveButtonClicked(params) {
        const result = await super.saveButtonClicked(...arguments);
        if (this.props.resModel === 'cabinet.rendezvous' && window._rdvRefreshBanner) {
            window._rdvRefreshBanner();
        }
        return result;
    },

    async discard() {
        if (this.props.resModel === 'cabinet.rendezvous' && this.model.root.resId) {
            try {
                await this.orm.call('cabinet.rendezvous', 'unlink', [[this.model.root.resId]]);
            } catch (e) {
                console.error("Erreur lors de la suppression du rendez-vous", e);
            }
            if (this.env.inDialog) {
                this.env.dialogData.dismiss();
                return;
            }
        }
        await super.discard(...arguments);
    }
});
