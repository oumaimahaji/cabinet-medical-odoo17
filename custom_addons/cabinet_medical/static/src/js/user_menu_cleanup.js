/** @odoo-module **/

import { registry } from "@web/core/registry";

const userMenuRegistry = registry.category("user_menuitems");

// Wait for registry initialization to complete, then remove the unwanted items
const itemsToRemove = ["documentation", "documentation_url", "support", "odoo_account"];

for (const item of itemsToRemove) {
    if (userMenuRegistry.contains(item)) {
        userMenuRegistry.remove(item);
        console.log(`[Cabinet Médical] Item '${item}' removed from Odoo user menu.`);
    }
}
