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

print("\n================ TOTAL SUMMARY ================")
total_ran = res1.testsRun + res2.testsRun + res3.testsRun + res4.testsRun + res5.testsRun + res6.testsRun + res7.testsRun + res8.testsRun
total_errors = len(res1.errors) + len(res2.errors) + len(res3.errors) + len(res4.errors) + len(res5.errors) + len(res6.errors) + len(res7.errors) + len(res8.errors)
total_failures = len(res1.failures) + len(res2.failures) + len(res3.failures) + len(res4.failures) + len(res5.failures) + len(res6.failures) + len(res7.failures) + len(res8.failures)
print(f"Total Unit Tests Ran: {total_ran}, Errors: {total_errors}, Failures: {total_failures}")


