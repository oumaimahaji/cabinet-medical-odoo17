/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUnmount, useEffect, markup } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

export class AIDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.charts = {};
        
        this.state = useState({
            loadingAI: true,
            aiHtml: "",
            aiStats: {},
            isMedecin: false,
            error: false,
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadAI();
        });

        useEffect(() => {
            if (!this.state.loadingAI && this.state.isMedecin && this.state.aiStats) {
                this.renderCharts();
            }
        });

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }

    async loadAI() {
        this.state.loadingAI = true;
        try {
            const result = await this.orm.call("cabinet.dashboard.ai", "get_ai_insights", []);
            if (result) {
                this.state.aiHtml    = markup(result.html);
                this.state.aiStats   = result.stats;
                this.state.isMedecin = result.stats.isMedecin;
            }
        } catch (error) {
            console.error("Erreur lors du chargement des insights IA:", error);
            this.state.error = true;
        } finally {
            this.state.loadingAI = false;
        }
    }

    renderCharts() {
        const stats = this.state.aiStats;
        if (!stats || typeof Chart === "undefined") return;

        // Configuration pour Bar et Line
        const linearOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 14,
                        font: { size: 12, weight: 'bold' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(33, 37, 41, 0.9)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    padding: 10,
                    cornerRadius: 6,
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11, weight: '500' }, color: '#6c757d' }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: '#f1f3f5' },
                    ticks: {
                        precision: 0,
                        font: { size: 11 },
                        color: '#6c757d'
                    }
                }
            }
        };

        // Configuration pour Pie et Doughnut (SANS axes cartésiens parasites)
        const circularOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {}, // AUCUN axe linéaire (évite les chiffres 0, 0.1, 0.2... et la grille)
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 14,
                        padding: 15,
                        font: { size: 12, weight: '500' },
                        color: '#495057'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(33, 37, 41, 0.9)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    padding: 10,
                    cornerRadius: 6,
                }
            }
        };

        // US35: Consultations par mois
        const canvas35 = document.getElementById("chart_us35");
        if (canvas35) {
            if (this.charts.us35) this.charts.us35.destroy();

            this.charts.us35 = new Chart(canvas35.getContext("2d"), {
                type: 'bar',
                data: {
                    labels: stats.us35_labels || [],
                    datasets: [{
                        label: 'Consultations',
                        data: stats.us35_data || [],
                        backgroundColor: '#17a2b8',
                        borderRadius: 6,
                        barPercentage: 0.6,
                    }]
                },
                options: linearOptions
            });
        }

        // US36: CA par Scénario
        const canvas36 = document.getElementById("chart_us36");
        if (canvas36) {
            if (this.charts.us36) this.charts.us36.destroy();

            // Filtrer les catégories à zéro pour ne pas afficher de segments vides
            const labels36 = stats.us36_labels || [];
            const data36   = stats.us36_data   || [];
            const filtered = labels36.map((l, i) => ({ label: l, val: data36[i] || 0 }))
                                     .filter(d => d.val > 0);

            this.charts.us36 = new Chart(canvas36.getContext("2d"), {
                type: 'doughnut',
                data: {
                    labels: filtered.length ? filtered.map(d => d.label) : ['Aucun CA'],
                    datasets: [{
                        data: filtered.length ? filtered.map(d => d.val) : [1],
                        backgroundColor: filtered.length ? ['#6c757d', '#28a745', '#17a2b8', '#dc3545'] : ['#e9ecef'],
                        borderWidth: 2,
                        borderColor: '#ffffff',
                    }]
                },
                options: {
                    ...circularOptions,
                    plugins: {
                        ...circularOptions.plugins,
                        tooltip: {
                            ...circularOptions.plugins.tooltip,
                            callbacks: {
                                label: (ctx) => ` ${ctx.label}: ${typeof ctx.parsed === 'number' ? ctx.parsed.toFixed(3) : ctx.parsed} DT`
                            }
                        }
                    }
                }
            });
        }

        // US37: CNAM en attente
        const canvas37 = document.getElementById("chart_us37");
        if (canvas37) {
            if (this.charts.us37) this.charts.us37.destroy();

            this.charts.us37 = new Chart(canvas37.getContext("2d"), {
                type: 'line',
                data: {
                    labels: stats.us37_labels || [],
                    datasets: [{
                        label: 'Montants en attente (DT)',
                        data: stats.us37_data || [],
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.2)',
                        borderWidth: 2.5,
                        pointBackgroundColor: '#ffc107',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        tension: 0.3,
                        fill: true,
                    }]
                },
                options: {
                    ...linearOptions,
                    scales: {
                        ...linearOptions.scales,
                        y: {
                            ...linearOptions.scales.y,
                            ticks: {
                                callback: (val) => `${val} DT`,
                                font: { size: 11 },
                                color: '#6c757d'
                            }
                        }
                    }
                }
            });
        }

        // US39: Camembert répartition patients
        const canvas39 = document.getElementById("chart_us39");
        if (canvas39) {
            if (this.charts.us39) this.charts.us39.destroy();

            const labels39 = stats.us39_labels || [];
            const data39   = stats.us39_data   || [];
            const colors39 = ['#0d6efd', '#dc3545', '#6c757d'];
            const filtered39 = labels39.map((l, i) => ({
                label: l,
                val: data39[i] || 0,
                color: colors39[i]
            })).filter(d => d.val > 0);

            this.charts.us39 = new Chart(canvas39.getContext("2d"), {
                type: 'pie',
                data: {
                    labels: filtered39.length ? filtered39.map(d => d.label) : ['Aucun patient'],
                    datasets: [{
                        data: filtered39.length ? filtered39.map(d => d.val) : [1],
                        backgroundColor: filtered39.length ? filtered39.map(d => d.color) : ['#e9ecef'],
                        borderWidth: 2,
                        borderColor: '#ffffff',
                    }]
                },
                options: circularOptions
            });
        }
    }
}

AIDashboard.template = "cabinet_medical.AIDashboard";

registry.category("actions").add("cabinet_medical_dashboard", AIDashboard);
