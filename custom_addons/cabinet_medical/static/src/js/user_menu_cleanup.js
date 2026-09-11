/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

const userMenuRegistry = registry.category("user_menuitems");

// Remove unwanted items
const itemsToRemove = ["documentation", "documentation_url", "support", "odoo_account"];

for (const item of itemsToRemove) {
    if (userMenuRegistry.contains(item)) {
        userMenuRegistry.remove(item);
    }
}

// Override logout label to French "Déconnexion"
function patchLogoutLabel() {
    const interval = setInterval(() => {
        // Target the logout/log out link in user menu dropdown
        const menuItems = document.querySelectorAll(
            '.o_user_menu .dropdown-item, .o_menu_systray .dropdown-item'
        );
        menuItems.forEach(item => {
            const text = item.textContent.trim();
            if (text === 'Log out' || text === 'Log Out' || text === 'Logout') {
                item.childNodes.forEach(node => {
                    if (node.nodeType === Node.TEXT_NODE && 
                        (node.textContent.trim() === 'Log out' || 
                         node.textContent.trim() === 'Log Out' ||
                         node.textContent.trim() === 'Logout')) {
                        node.textContent = ' D\u00e9connexion';
                    }
                });
            }
            // Also handle Preferences label
            if (text === 'Preferences') {
                item.childNodes.forEach(node => {
                    if (node.nodeType === Node.TEXT_NODE && node.textContent.trim() === 'Preferences') {
                        node.textContent = ' Pr\u00e9f\u00e9rences';
                    }
                });
            }
            // My Profile
            if (text === 'My Profile' || text === 'Profile') {
                item.childNodes.forEach(node => {
                    if (node.nodeType === Node.TEXT_NODE && 
                       (node.textContent.trim() === 'My Profile' || node.textContent.trim() === 'Profile')) {
                        node.textContent = ' Mon Profil';
                    }
                });
            }
        });
    }, 500);
    // Stop after 30 seconds
    setTimeout(() => clearInterval(interval), 30000);
}

patchLogoutLabel();
