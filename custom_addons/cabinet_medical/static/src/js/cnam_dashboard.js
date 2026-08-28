/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class CnamDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        
        const today = new Date();
        this.state = useState({
            loading: true,
            month: today.getMonth() + 1,
            year: today.getFullYear(),
            stats: {
                envoyes: { count: 0, amount: 0 },
                attente: { count: 0, amount: 0, avg_days: 0 },
                payes: { count: 0, amount: 0 },
                rejetes: []
            },
            error: false,
        });

        onWillStart(async () => {
            await this.loadStats();
        });
    }

    async loadStats() {
        this.state.loading = true;
        this.state.error = false;
        try {
            const result = await this.orm.call(
                "cabinet.bordereau",
                "get_cnam_dashboard_stats",
                [],
                {
                    month: this.state.month,
                    year: this.state.year
                }
            );
            if (result) {
                this.state.stats = result;
            }
        } catch (error) {
            console.error("Erreur lors du chargement des stats CNAM:", error);
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }

    onMonthChange(ev) {
        this.state.month = parseInt(ev.target.value);
        this.loadStats();
    }
    
    onYearChange(ev) {
        this.state.year = parseInt(ev.target.value);
        this.loadStats();
    }
}

CnamDashboard.template = "cabinet_medical.CnamDashboard";

registry.category("actions").add("cabinet_medical_cnam_dashboard", CnamDashboard);
