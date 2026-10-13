import unittest
import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Run test_bdpm_ontology
print("=== RUNNING test_bdpm_ontology.py ===")
suite1 = unittest.defaultTestLoader.discover(test_dir, pattern='test_bdpm_ontology.py')
res1 = unittest.TextTestRunner(verbosity=2).run(suite1)

# 2. Run test_prescription_ia
print("\n=== RUNNING test_prescription_ia.py ===")
suite2 = unittest.defaultTestLoader.discover(test_dir, pattern='test_prescription_ia.py')
res2 = unittest.TextTestRunner(verbosity=2).run(suite2)

# 3. Run test_no_show_pipeline
print("\n=== RUNNING test_no_show_pipeline.py ===")
suite3 = unittest.defaultTestLoader.discover(test_dir, pattern='test_no_show_pipeline.py')
res3 = unittest.TextTestRunner(verbosity=2).run(suite3)

# 4. Run test_res_users
print("\n=== RUNNING test_res_users.py ===")
suite4 = unittest.defaultTestLoader.discover(test_dir, pattern='test_res_users.py')
res4 = unittest.TextTestRunner(verbosity=2).run(suite4)

# 5. Run test_cnam_groupe1
print("\n=== RUNNING test_cnam_groupe1.py ===")
suite5 = unittest.defaultTestLoader.discover(test_dir, pattern='test_cnam_groupe1.py')
res5 = unittest.TextTestRunner(verbosity=2).run(suite5)

# 6. Run test_cnam_groupe2
print("\n=== RUNNING test_cnam_groupe2.py ===")
suite6 = unittest.defaultTestLoader.discover(test_dir, pattern='test_cnam_groupe2.py')
res6 = unittest.TextTestRunner(verbosity=2).run(suite6)

# 7. Run test_cnam_groupe3
print("\n=== RUNNING test_cnam_groupe3.py ===")
suite7 = unittest.defaultTestLoader.discover(test_dir, pattern='test_cnam_groupe3.py')
res7 = unittest.TextTestRunner(verbosity=2).run(suite7)

# 8. Run test_cnam_groupe4
print("\n=== RUNNING test_cnam_groupe4.py ===")
suite8 = unittest.defaultTestLoader.discover(test_dir, pattern='test_cnam_groupe4.py')
res8 = unittest.TextTestRunner(verbosity=2).run(suite8)

# 9. Run test_unique_consultation_facture
print("\n=== RUNNING test_unique_consultation_facture.py ===")
suite9 = unittest.defaultTestLoader.discover(test_dir, pattern='test_unique_consultation_facture.py')
res9 = unittest.TextTestRunner(verbosity=2).run(suite9)

# 10. Run test_sprint1_patient_import
print("\n=== RUNNING test_sprint1_patient_import.py ===")
suite10 = unittest.defaultTestLoader.discover(test_dir, pattern='test_sprint1_patient_import.py')
res10 = unittest.TextTestRunner(verbosity=2).run(suite10)

# 11. Run test_tunisian_pharmacology
print("\n=== RUNNING test_tunisian_pharmacology.py ===")
suite11 = unittest.defaultTestLoader.discover(test_dir, pattern='test_tunisian_pharmacology.py')
res11 = unittest.TextTestRunner(verbosity=2).run(suite11)

print("\n================ TOTAL SUMMARY ================")
all_results = [res1, res2, res3, res4, res5, res6, res7, res8, res9, res10, res11]
total_ran = sum(r.testsRun for r in all_results)
total_errors = sum(len(r.errors) for r in all_results)
total_failures = sum(len(r.failures) for r in all_results)
print(f"Total Unit Tests Ran: {total_ran}, Errors: {total_errors}, Failures: {total_failures}")
sys.exit(1 if (total_errors or total_failures) else 0)


