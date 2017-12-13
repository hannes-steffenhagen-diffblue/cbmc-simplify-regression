import test_base
import argparse

options_parser = argparse.ArgumentParser(parents=[test_base.options_parser])

options = options_parser.parse_args()


def normalize_asserts(asserts):
  l_asserts = asserts.split(b'\n')
  return b'\n'.join(sorted(l_asserts))


class SimplifyVerifyTest(test_base.TestBase):
  def __init__(self, options):
    super().__init__(options)

  def run_test(self, goto, simplified_goto):
    verified = normalize_asserts(self.show_verified_asserts(goto))
    simplified_verified = normalize_asserts(self.show_verified_asserts(simplified_goto))
    if verified == simplified_verified:
      return test_base.TestResult.SUCCESS
    else:
      return test_base.TestResult.FAILURE


test_runner = SimplifyVerifyTest(options)
test_runner.run()
