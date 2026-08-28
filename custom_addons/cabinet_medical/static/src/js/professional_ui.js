/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { session } from "@web/session";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { X2ManyFieldDialog } from "@web/views/fields/relational_utils";

// Cacher l'app switcher (icône 9 carrés) pour les utilisateurs qui ne sont pas admin
const hideAppSwitcher = () => {
    if (session.uid !== 1) {
        document.body.classList.add('hide_app_switcher');
        const toggleBtn = document.querySelector('.o_navbar_apps_menu, .o_menu_toggle');
        if (toggleBtn) {
            toggleBtn.style.setProperty('display', 'none', 'important');
        }
    }
};

if (document.body) {
    hideAppSwitcher();
} else {
    document.addEventListener("DOMContentLoaded", hideAppSwitcher);
}

// Odoo recharge parfois la navbar dynamiquement (SPA), on force la vérification
setInterval(hideAppSwitcher, 500);

patch(ActionMenus.prototype, {
    async getActionItems(props) {
        const items = await super.getActionItems(props);
        if (items) {
            for (const item of items) {
                if (item.description && item.description.toLowerCase().includes("import")) {
                    item.icon = "fa fa-upload";
                }
            }
        }
        return items;
    }
});

// 1. Correction des icônes dans les breadcrumbs (titres de page)
// On utilise un setInterval très léger pour s'assurer que l'icône est toujours là
setInterval(function () {
    // Cibler tous les éléments qui pourraient être le titre actif
    var breadcrumbs = document.querySelectorAll('.o_control_panel_breadcrumbs .breadcrumb-item.active, .o_breadcrumb .active, .breadcrumb-item.active span');

    breadcrumbs.forEach(function (el) {
        if (!el) return;
        var text = el.innerText.trim();

        // Si le texte est exactement le nom de la page sans icône, on ajoute l'icône
        if (text === "Patients") {
            el.innerText = "👥 Liste des Patients";
        } else if (text === "Assurances") {
            el.innerText = "🛡️ Liste des Assurances";
        } else if (text === "Consultations") {
            el.innerText = "🩺 Liste des Consultations";
        } else if (text === "Rendez-vous") {
            el.innerText = "📅 Liste des Rendez-vous";
        } else if (text === "Facturations") {
            el.innerText = "💳 Liste des Facturations";
        }
    });
}, 500);

// Fonction utilitaire pour aller à une page spécifique via le pager natif d'Odoo
if (!window._goToPage) {
    window._goToPage = function(page, pageSize, topPager) {
        let valueEl = topPager.querySelector('.o_pager_value');
        if (valueEl && !topPager.querySelector('input')) {
            valueEl.click(); // Transforme le span en input
        }
        setTimeout(() => {
            let input = topPager.querySelector('input');
            if (input) {
                let newStart = (page - 1) * pageSize + 1;
                input.value = newStart.toString();
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
                input.blur();
            } else {
                // Fallback: use next/prev buttons if input edit fails
                let currentStart = parseInt((topPager.textContent.match(/(\d+)-/) || [0,1])[1], 10);
                let currentPage = Math.floor((currentStart - 1) / pageSize) + 1;
                let diff = page - currentPage;
                if (diff > 0) {
                    let nextBtn = topPager.querySelector('.o_pager_next');
                    for(let i=0; i<diff; i++) if (nextBtn && !nextBtn.disabled) nextBtn.click();
                } else if (diff < 0) {
                    let prevBtn = topPager.querySelector('.o_pager_previous');
                    for(let i=0; i<Math.abs(diff); i++) if (prevBtn && !prevBtn.disabled) prevBtn.click();
                }
            }
        }, 50);
    };
}

// 2. Déplacement de la pagination en bas du tableau (façon professionnelle avec NUMÉROS)
setInterval(function () {
    // Chercher le tableau principal (ou vue kanban)
    var viewRenderer = document.querySelector('.o_list_renderer, .o_kanban_renderer');
    // Chercher le pager du haut (plus générique)
    var topPager = document.querySelector('.o_pager');

    if (viewRenderer && topPager) {
        // Créer un conteneur pour la pagination en bas s'il n'existe pas
        var bottomPagerContainer = document.querySelector('.custom_bottom_pager_container');

        if (!bottomPagerContainer) {
            bottomPagerContainer = document.createElement('div');
            bottomPagerContainer.className = 'custom_bottom_pager_container';
            // Ajouter le conteneur juste après le renderer
            if (viewRenderer.parentNode) {
                viewRenderer.parentNode.insertBefore(bottomPagerContainer, viewRenderer.nextSibling);
            }
        }

        // Structure de base
        if (bottomPagerContainer.children.length === 0) {
            var leftDiv = document.createElement('div');
            leftDiv.className = 'pager_info_text';
            
            var rightDiv = document.createElement('div');
            rightDiv.className = 'pager_buttons';
            
            bottomPagerContainer.appendChild(leftDiv);
            bottomPagerContainer.appendChild(rightDiv);
        }

        // --- SYNCHRONISATION ET GÉNÉRATION DE LA PAGINATION NUMÉROTÉE ---
        // Essayer de trouver les éléments spécifiques, sinon utiliser le texte global
        var originalValueEl = topPager.querySelector('.o_pager_value');
        var originalLimitEl = topPager.querySelector('.o_pager_limit');
        
        let valueStr = '';
        let limitStr = '';
        let isValidPager = false;

        if (topPager.querySelector('input')) {
            // En cours d'édition, on ne met pas à jour
            return;
        }

        if (originalValueEl && originalLimitEl) {
            valueStr = originalValueEl.textContent.trim();
            limitStr = originalLimitEl.textContent.trim();
            isValidPager = (valueStr !== '' && limitStr !== '');
        } else {
            // Fallback pour extraire du texte (ex: "1-6 / 10")
            let text = topPager.textContent.replace(/\s+/g, ''); // "1-6/10"
            let match = text.match(/(\d+(?:-\d+)?)\/(\d+)/);
            if (match) {
                valueStr = match[1];
                limitStr = match[2];
                isValidPager = true;
            }
        }
        
        if (isValidPager) {
            bottomPagerContainer.style.display = 'flex';
            
            const total = parseInt(limitStr.replace(/\D/g, ''), 10) || 0;
            let start = 1, end = 1;
            
            if (valueStr.includes('-')) {
                const parts = valueStr.split('-');
                start = parseInt(parts[0].replace(/\D/g, ''), 10) || 1;
                end = parseInt(parts[1].replace(/\D/g, ''), 10) || 1;
            } else {
                start = parseInt(valueStr.replace(/\D/g, ''), 10) || 1;
                end = start;
            }
            
            // Détection de la taille de page
            if (!window._detectedPageSize) window._detectedPageSize = 10; // Limite par défaut
            const currentSize = end - start + 1;
            // Si la page est pleine, on met à jour la taille
            if (currentSize >= window._detectedPageSize || (end < total && currentSize > 0)) {
                window._detectedPageSize = currentSize;
            }
            const pageSize = window._detectedPageSize;
            
            const totalPages = Math.ceil(total / pageSize) || 1;
            const currentPage = Math.floor((start - 1) / pageSize) + 1;
            
            // 1. Mise à jour du texte à gauche (Affichage de 1-6 sur 10)
            var infoDiv = bottomPagerContainer.querySelector('.pager_info_text');
            const infoTextState = `${valueStr}-${limitStr}`;
            if (infoDiv.getAttribute('data-state') !== infoTextState) {
                infoDiv.setAttribute('data-state', infoTextState);
                infoDiv.innerHTML = `Affichage de <span class="o_pager_counter custom_counter">${valueStr}</span> sur <strong>${limitStr}</strong> résultats`;
            }
            
            // 2. Mise à jour des boutons numérotés à droite
            var buttonsDiv = bottomPagerContainer.querySelector('.pager_buttons');
            const paginationState = `${currentPage}-${totalPages}-${pageSize}`;
            
            if (buttonsDiv.getAttribute('data-state') !== paginationState) {
                buttonsDiv.setAttribute('data-state', paginationState);
                buttonsDiv.innerHTML = ''; // On vide et on recrée les boutons
                
                // --- Bouton Précédent ---
                let prevBtn = document.createElement('button');
                prevBtn.className = 'btn custom-pager-btn';
                prevBtn.innerHTML = '<i class="fa fa-chevron-left"></i>';
                prevBtn.disabled = (currentPage <= 1);
                prevBtn.onclick = function() {
                    let topPrev = topPager.querySelector('.o_pager_previous');
                    if (topPrev && !topPrev.disabled) topPrev.click();
                };
                buttonsDiv.appendChild(prevBtn);
                
                // --- Boutons de pages (ex: 1 2 3 ... 10) ---
                let maxPagesToShow = 5;
                let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
                let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
                
                // Ajustement si on est près de la fin
                if (endPage - startPage + 1 < maxPagesToShow) {
                    startPage = Math.max(1, endPage - maxPagesToShow + 1);
                }
                
                // Page 1 et points de suspension si nécessaire
                if (startPage > 1) {
                    let firstBtn = document.createElement('button');
                    firstBtn.className = 'btn custom-pager-btn';
                    firstBtn.innerText = '1';
                    firstBtn.onclick = () => window._goToPage(1, pageSize, topPager);
                    buttonsDiv.appendChild(firstBtn);
                    
                    if (startPage > 2) {
                        let dots = document.createElement('span');
                        dots.className = 'pager-dots';
                        dots.innerText = '...';
                        buttonsDiv.appendChild(dots);
                    }
                }
                
                // Boucle sur les pages centrales
                for (let i = startPage; i <= endPage; i++) {
                    let pageBtn = document.createElement('button');
                    pageBtn.className = 'btn custom-pager-btn' + (i === currentPage ? ' active-page' : '');
                    pageBtn.innerText = i;
                    if (i === currentPage) {
                        pageBtn.disabled = true;
                    } else {
                        pageBtn.onclick = () => window._goToPage(i, pageSize, topPager);
                    }
                    buttonsDiv.appendChild(pageBtn);
                }
                
                // Dernière page et points de suspension si nécessaire
                if (endPage < totalPages) {
                    if (endPage < totalPages - 1) {
                        let dots = document.createElement('span');
                        dots.className = 'pager-dots';
                        dots.innerText = '...';
                        buttonsDiv.appendChild(dots);
                    }
                    let lastBtn = document.createElement('button');
                    lastBtn.className = 'btn custom-pager-btn';
                    lastBtn.innerText = totalPages;
                    lastBtn.onclick = () => window._goToPage(totalPages, pageSize, topPager);
                    buttonsDiv.appendChild(lastBtn);
                }
                
                // --- Bouton Suivant ---
                let nextBtn = document.createElement('button');
                nextBtn.className = 'btn custom-pager-btn';
                nextBtn.innerHTML = '<i class="fa fa-chevron-right"></i>';
                nextBtn.disabled = (currentPage >= totalPages);
                nextBtn.onclick = function() {
                    let topNext = topPager.querySelector('.o_pager_next');
                    if (topNext && !topNext.disabled) topNext.click();
                };
                buttonsDiv.appendChild(nextBtn);
            }
        } else {
            bottomPagerContainer.style.display = 'none';
        }
    } else {
        // If no top pager or renderer is found, hide the bottom pager if it exists
        var bottomPagerContainer = document.querySelector('.custom_bottom_pager_container');
        if (bottomPagerContainer) bottomPagerContainer.style.display = 'none';
    }
}, 300);

// -------------------------------------------------------------------------
// FEEDBACK VISUEL IMMÉDIAT : BOUTON "VÉRIFIER AVEC L'IA"
// -------------------------------------------------------------------------
document.addEventListener('click', function (e) {
    const btn = e.target.closest('button[name="action_verifier_ia"]');
    if (!btn) return;

    if (btn.classList.contains('o_ai_analyzing')) {
        return;
    }

    if (!btn.getAttribute('data-original-html')) {
        btn.setAttribute('data-original-html', btn.innerHTML);
    }

    // Affichage immédiat du spinner
    btn.classList.add('o_ai_analyzing');
    btn.innerHTML = '<i class="fa fa-spinner fa-spin mr-1"></i> 🤖 Analyse en cours…';
    btn.style.opacity = '0.85';

    const resetButton = () => {
        if (btn && btn.classList.contains('o_ai_analyzing')) {
            btn.classList.remove('o_ai_analyzing');
            btn.innerHTML = btn.getAttribute('data-original-html') || '🤖 Vérifier avec l\'IA';
            btn.style.opacity = '';
        }
    };

    // Réinitialisation après la réponse quasi-instantanée (~35ms backend)
    setTimeout(resetButton, 1200);
}, false);

// -------------------------------------------------------------------------
// SYNCHRONISATION DU MODÈLE ODOO OWL : SUPPRESSION DE LIGNE DANS L'ORDONNANCE
// -------------------------------------------------------------------------
patch(X2ManyField.prototype, {
    setup() {
        super.setup();
        if (this.props.name === "ordonnance_line_ids") {
            const originalOnDelete = this.activeActions.onDelete;
            if (originalOnDelete) {
                this.activeActions.onDelete = async (record) => {
                    await originalOnDelete(record);
                    const parentRecord = this.props.record;
                    if (parentRecord && (parentRecord.resModel === "cabinet.prescription" || parentRecord.fields.ia_statut)) {
                        // Réinitialise l'état IA à 'non_verifie' immédiatement sans relancer l'IA
                        await parentRecord.update({
                            ia_statut: "non_verifie",
                            ia_message: false,
                            ia_fingerprint: false,
                        });
                    }
                };
            }
        }
    }
});

// -------------------------------------------------------------------------
// SUPPRESSION DE L'OVERLAY DE CHARGEMENT POUR TOUTES LES IMPRESSIONS (ORDONNANCE, FACTURE, REÇU, CNAM, MUTUELLE, BORDEREAU)
// -------------------------------------------------------------------------
document.addEventListener('click', function (e) {
    const btn = e.target.closest('button');
    if (!btn) return;

    const name = btn.getAttribute('name') || '';
    const text = (btn.innerText || '').trim();
    const isPrintButton = (
        name === 'action_imprimer_ordonnance' ||
        name.includes('action_report_') ||
        ['176', '177', '178', '179', '183', '190'].includes(name) ||
        text.includes('Imprimer') ||
        text.includes('Bulletin de Soins') ||
        text.includes('Formulaire de remboursement') ||
        text.includes('Feuille de Soins') ||
        text.includes('Bordereau') ||
        btn.querySelector('.fa-print') !== null
    );

    if (!isPrintButton) return;

    const hideLoader = () => {
        const blockUIs = document.querySelectorAll('.o_blockUI, .o_loading_indicator');
        blockUIs.forEach(el => {
            el.style.setProperty('display', 'none', 'important');
        });
    };

    hideLoader();

    const observer = new MutationObserver(function () {
        hideLoader();
    });

    observer.observe(document.body, { childList: true, subtree: true });

    setTimeout(() => {
        observer.disconnect();
    }, 4000);
}, true);

// -------------------------------------------------------------------------
// SYNCHRONISATION INSTANTANÉE DE LA LISTE DES ORDONNANCES (SANS F5 NI HARD RELOAD)
// -------------------------------------------------------------------------
patch(X2ManyFieldDialog.prototype, {
    async beforeExecuteActionButton(clickParams) {
        const res = await super.beforeExecuteActionButton(clickParams);
        if (clickParams.name === "action_save_prescription" && this.props.save) {
            await this.props.save(this.record);
        }
        return res;
    },
});


