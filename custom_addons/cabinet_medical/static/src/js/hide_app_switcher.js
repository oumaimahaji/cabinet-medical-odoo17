/** @odoo-module **/

/**
 * ============================================================
 *  hide_app_switcher.js — Cabinet Médical
 * ============================================================
 *
 *  ⚠ AVERTISSEMENT SÉCURITÉ :
 *  Ce fichier JS est une COUCHE DE RENDU COMPLÉMENTAIRE uniquement.
 *  Il ne constitue PAS une barrière de sécurité réelle.
 *
 *  La vraie protection est côté SERVEUR (QWeb) dans hide_waffle_view.xml :
 *  → La classe "o_cabinet_restricted" est injectée dans <body> dès le
 *    premier rendu HTML, avant que ce JS s'exécute.
 *  → Ce service JS détecte simplement si la classe est présente pour
 *    loguer l'état, sans modifier le DOM (ce serait redondant et fragile).
 *
 *  POURQUOI SUPPRIMER LE setInterval() ?
 *  • Le setInterval qui supprime le nœud DOM toutes les 500ms est instable :
 *    il peut casser des composants Owl qui recréent le menu légitimement.
 *  • La classe CSS sur <body> + hide_apps_menu.css suffit amplement.
 *  • Supprimer un nœud React/Owl en dehors du framework = memory leaks.
 * ============================================================
 */

import { registry } from "@web/core/registry";

const hideWaffleService = {
    dependencies: [],

    start(env) {
        // Vérification passive : la classe a-t-elle bien été posée par le serveur ?
        const bodyRestricted = document.body.classList.contains("o_cabinet_restricted");

        if (bodyRestricted) {
            console.info(
                "[Cabinet Médical] Profil restreint détecté. " +
                "Le menu Waffle est masqué via la classe serveur 'o_cabinet_restricted'."
            );
            // ✅ Rien de plus à faire : le CSS hide_apps_menu.css gère le rendu.
        }
        // Si la classe n'est pas là, l'utilisateur est admin/autre → comportement normal.
    }
};

registry.category("services").add("cabinet_medical_hide_waffle", hideWaffleService);
