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

print("\n================ TOTAL SUMMARY ================")
total_ran = res1.testsRun + res2.testsRun + res3.testsRun
total_errors = len(res1.errors) + len(res2.errors) + len(res3.errors)
total_failures = len(res1.failures) + len(res2.failures) + len(res3.failures)
print(f"Total Unit Tests Ran: {total_ran}, Errors: {total_errors}, Failures: {total_failures}")

