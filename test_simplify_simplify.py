import test_base
import argparse
import re

options_parser = argparse.ArgumentParser(parents=[test_base.options_parser])
options = options_parser.parse_args()


def is_comment(line):
  return bool(re.match(br'^\s*//', line))


def is_empty(line):
  return bool(re.match(br'^\s*$', line))


# remove comments and sort blocks
def normalize_goto_code(goto_code):
  block_sep = b'^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'
  blocks = goto_code.split(block_sep)
  normalized_blocks = []
  for block in blocks:
    lines = block.split(b"\n")
    new_lines = filter(lambda ln: not (is_comment(ln) or is_empty(ln)), lines)
    normalized_blocks.append(b"\n".join(new_lines))
  return b"\n".join(sorted(normalized_blocks))


class SimplifySimplifyTest(test_base.TestBase):
  def __init__(self, options):
    super().__init__(options)
    self.reg_goto_extension = re.compile(r'\.goto$')

  def run_test(self, goto, simplified_goto):
    simple_goto_functions = self.show_goto_as_string(simplified_goto)
    normalized_simple_goto_functions = normalize_goto_code(simple_goto_functions)
    simplified_simple_goto = re.sub(self.reg_goto_extension, '-simple.goto', simplified_goto)
    self.simplify_goto(simplified_goto, simplified_simple_goto)
    simplified_simple_goto_functions = self.show_goto_as_string(simplified_simple_goto)
    normalized_simplified_simple_goto_functions = normalize_goto_code(simplified_simple_goto_functions)
    if normalized_simple_goto_functions == normalized_simplified_simple_goto_functions:
      return test_base.TestResult.SUCCESS
    else:
      return test_base.TestResult.FAILURE


test_runner = SimplifySimplifyTest(options)
test_runner.run()
