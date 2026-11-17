import unittest
import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))


def _is_odoo_integration_test(filepath):
    """Détecte les fichiers utilisant TransactionCase/HttpCase (exécutés via odoo-bin --test-enable)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            head = f.read(2048)
        return 'odoo.tests.common' in head or 'TransactionCase' in head
    except OSError:
        return False


# Découverte dynamique : tous les fichiers test_*.py du dossier, triés pour
# garantir un ordre d'exécution reproductible.
test_files = sorted([
    f for f in os.listdir(test_dir)
    if f.startswith("test_") and f.endswith(".py")
])

all_results = []
load_errors = 0
for test_file in test_files:
    full_path = os.path.join(test_dir, test_file)
    if _is_odoo_integration_test(full_path):
        print(f"\n=== SKIPPING {test_file} (tests d'intégration Odoo -> exécuter avec odoo-bin --test-enable) ===")
        continue
    print(f"\n=== RUNNING {test_file} ===")
    suite = unittest.defaultTestLoader.discover(test_dir, pattern=test_file)
    # Vérifier que la suite contient au moins un test chargé (détecte les
    # erreurs d'import silencieuses).
    if suite.countTestCases() == 0:
        print(f"  [AVERTISSEMENT] Aucun test découvert dans {test_file}")
        load_errors += 1
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    all_results.append(res)

print("\n================ TOTAL SUMMARY ================")
total_ran = sum(r.testsRun for r in all_results)
total_errors = sum(len(r.errors) for r in all_results)
total_failures = sum(len(r.failures) for r in all_results)
print(
    f"Total Unit Tests Ran: {total_ran}, "
    f"Errors: {total_errors}, Failures: {total_failures}"
)
sys.exit(1 if (total_errors or total_failures or load_errors) else 0)
