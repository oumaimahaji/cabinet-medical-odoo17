/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CabinetNotificationSystray extends Component {
    static template = "cabinet_medical.NotificationSystray";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");
        this.notification = useService("notification");

        this.state = useState({
            isOpen: false,
            alerts: [],
            unreadCount: 0,
        });

        this.isSecretaire = false;

        this.onWindowClick = (ev) => {
            if (this.state.isOpen && !ev.target.closest(".o_cabinet_notification_systray")) {
                this.state.isOpen = false;
            }
        };

        onWillStart(async () => {
            await this.loadAlerts();
        });

        onMounted(() => {
            window.addEventListener("click", this.onWindowClick);
        });

        onWillUnmount(() => {
            window.removeEventListener("click", this.onWindowClick);
        });
    }

    async loadAlerts() {
        try {
            const res = await this.orm.call("cabinet.patient", "get_secretary_cnam_alerts", []);
            if (res) {
                this.state.alerts = res.alerts || [];
                this.state.unreadCount = res.count || 0;
            }
        } catch (err) {
            console.warn("[Cabinet Médical] Erreur chargement alertes systray :", err);
        }
    }

    toggleDropdown(ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.isOpen = !this.state.isOpen;
    }

    async refreshAlerts(ev) {
        if (ev) {
            ev.stopPropagation();
        }
        await this.loadAlerts();
        this.notification.add(
            `Analyse IA effectuée : ${this.state.unreadCount} alerte(s) active(s)`,
            { type: "info", title: "Veille Proactive CNAM" }
        );
    }

    openPatient(patientId) {
        this.state.isOpen = false;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cabinet.patient",
            res_id: patientId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllPatients(ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.isOpen = false;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Liste des Patients",
            res_model: "cabinet.patient",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

export const systrayItem = {
    Component: CabinetNotificationSystray,
};

registry.category("systray").add("cabinet_medical.notification_systray", systrayItem, { sequence: 1 });
