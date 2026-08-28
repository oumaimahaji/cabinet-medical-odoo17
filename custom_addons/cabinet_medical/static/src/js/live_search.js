/** @odoo-module **/

import { SearchBar } from "@web/search/search_bar/search_bar";
import { patch } from "@web/core/utils/patch";

patch(SearchBar.prototype, {
    setup() {
        super.setup(...arguments);
        this._liveSearchTimeout = null;
        this._liveFacetGroupId = null;
    },

    onSearchInput(ev) {
        // Appeler le comportement standard pour afficher les suggestions
        super.onSearchInput(ev);

        // Vérifier si on est dans le module cabinet_medical
        const resModel = this.env.searchModel?.resModel;
        if (!resModel || !resModel.startsWith('cabinet.')) {
            return;
        }

        const query = ev.target.value;
        const trimmedQuery = query.trim();

        if (this._liveSearchTimeout) {
            clearTimeout(this._liveSearchTimeout);
        }

        if (trimmedQuery) {
            this._liveSearchTimeout = setTimeout(() => {
                const items = this.items;
                if (items && items.length > 0) {
                    // Prendre la première suggestion (généralement la recherche par nom)
                    const focusedItem = items.find(item => !item.unselectable);
                    if (focusedItem) {
                        // Retirer l'ancien filtre dynamique s'il existe
                        if (this._liveFacetGroupId) {
                            this.env.searchModel.deactivateGroup(this._liveFacetGroupId);
                        }

                        const { searchItemId, label, operator, value } = focusedItem;
                        // Déclencher la recherche (ceci réinitialise le champ de recherche)
                        this.env.searchModel.addAutoCompletionValues(searchItemId, { label, operator, value });

                        // Récupérer l'ID du nouveau groupe pour le nettoyer plus tard
                        const facets = this.env.searchModel.facets;
                        if (facets.length) {
                            this._liveFacetGroupId = facets[facets.length - 1].groupId;
                            // Optionnel: masquer visuellement cette facette via une classe CSS spécifique si possible
                            // document.body.classList.add('o_live_search_active');
                        }

                        // Restaurer la saisie de l'utilisateur instantanément
                        setTimeout(() => {
                            if (this.inputRef && this.inputRef.el) {
                                this.inputRef.el.value = query;
                                this.inputRef.el.focus();
                                this.inputRef.el.selectionStart = query.length;
                                this.inputRef.el.selectionEnd = query.length;
                                this.state.query = query; // Garder les suggestions ouvertes
                            }
                        }, 0);
                    }
                }
            }, 350); // 350ms de délai (debounce) pour ne pas spammer le serveur
        } else {
            // Si le champ est vide, nettoyer le filtre dynamique
            if (this._liveFacetGroupId) {
                this.env.searchModel.deactivateGroup(this._liveFacetGroupId);
                this._liveFacetGroupId = null;
            }
        }
    }
});
