# Module test_base

import argparse
import os
import subprocess
import sys
import tempfile
import glob
import shutil
import enum

base_path = os.path.dirname(os.path.realpath(sys.argv[0]))

options_parser = argparse.ArgumentParser(add_help=False)
options_parser.add_argument('--goto-cc', type=str, default='goto-cc',
                            help='Executable name for goto-cc (default: %(default)s)')
options_parser.add_argument('--goto-analyzer', type=str, default='goto-analyzer',
                            help='''Executable name for goto-analyzer
                            (default: %(default)s)''')
options_parser.add_argument('--goto-instrument', type=str, default='goto-instrument',
                            help='''Executable name for goto-instrument
                                (default: %(default)s)''')
options_parser.add_argument('--timeout', type=int, default=5,
                            help='''Timeout (in seconds) to use when running external tools
                              (default: %(default)d)''')

options_parser.add_argument('--exclusions-file', default=os.path.join(base_path, 'exclusions.txt'),
                            help='''Exclude source listed in this file from testing (if it exists)
                              (default: %(default)s)''')

options_parser.add_argument('--benchmarks-path', default=os.path.join(base_path, 'sv-benchmarks'),
                            help='''Use benchmarks from this directory (default: %(default)s)''')


def null_file():
  if os.name == 'nt':
    nullfile_name = 'NUL'
  else:
    nullfile_name = '/dev/null'
  return open(nullfile_name, 'w')


class Counters:
  def __init__(self):
    self.file_count = 0
    self.success_count = 0
    self.skip_count = 0
    self.timeout_count = 0
    self.failure_count = 0
    self.error_count = 0

  def files(self):
    return self.file_count

  def add_file(self):
    self.file_count = self.file_count + 1

  def successes(self):
    return self.success_count

  def add_success(self):
    self.success_count = self.success_count + 1

  def skips(self):
    return self.skip_count

  def add_skip(self):
    self.skip_count = self.skip_count + 1

  def failures(self):
    return self.failure_count

  def add_failure(self):
    self.failure_count = self.failure_count + 1

  def timeouts(self):
    return self.timeout_count

  def add_timeout(self):
    self.timeout_count = self.timeout_count + 1

  def errors(self):
    return self.error_count

  def add_error(self):
    self.error_count = self.error_count + 1


class TestResult(enum.Enum):
  # Test succeeded
  SUCCESS = 0
  # Test failed
  FAILURE = 1
  # Skipped the test
  SKIP = 2
  # One of the tools took more time than the timeout parameter
  TIMEOUT = 3
  # One of the tools returned an error
  ERROR = 4


class TestBase:
  def __init__(self, options):
    self.goto_cc = options.goto_cc
    self.goto_analyzer = options.goto_analyzer
    self.goto_instrument = options.goto_instrument

    try:
      with open(options.exclusions_file, 'r') as exclusions_file:
        self.test_exclusions = exclusions_file.readlines()
    except FileNotFoundError:
      self.test_exclusions = []

    self.script_timeout = options.timeout
    self.counters = Counters()
    self.base_path = base_path
    self.benchmarks_path = options.benchmarks_path
    self.c_benchmarks_path = os.path.join(self.benchmarks_path, 'c')

    self.download_benchmarks()

  def download_benchmarks(self):
    # download test sources
    # TODO the C code should probably be a part of internal repo for actual testing
    if not os.path.isdir(self.benchmarks_path):
      subprocess.check_call(['git', 'clone', 'https://github.com/sosy-lab/sv-benchmarks.git',
                             self.benchmarks_path,
                             '--depth', 1])

  def compile_goto(self, in_file, out_file=None):
    goto_cc_argv = [self.goto_cc, in_file]
    if out_file:
      goto_cc_argv += ['-o', out_file]
    with null_file() as dev_null:
      subprocess.check_call(goto_cc_argv, stdout=dev_null, timeout=self.script_timeout)

  def simplify_goto(self, in_file, out_file):
    with null_file() as dev_null:
      subprocess.check_call([self.goto_analyzer, in_file, '--simplify', out_file, '--variable', '--arrays', '--structs',
                       '--no-simplify-slicing'], stdout=dev_null, timeout=self.script_timeout)

  def show_goto_as_string(self, in_file):
    goto_functions = subprocess.check_output(
      [self.goto_instrument, in_file, '--show-goto-functions'],
      timeout=self.script_timeout)
    # The first 3 lines are discarded because they're just
    # info from goto-instrument rather than part of the code
    goto_functions_with_removed_header = b"\n".join(goto_functions.split(b"\n")[3:])
    return goto_functions_with_removed_header

  def show_verified_asserts(self, in_file):
    asserts = subprocess.check_output(
      [self.goto_analyzer, in_file, '--verify', '--variable', '--arrays', '--structs'],
      timeout=self.script_timeout)
    assert_lines = asserts.split(b"\n")
    # Find the last line of the header
    last_header_index = assert_lines.index(b'Checking assertions')
    # we don't want the header, so strip it
    return b"\n".join(assert_lines[last_header_index + 1:])

  def run_test(self, goto, simplified_goto):
    pass

  def run(self):
    tmpdir = tempfile.mkdtemp('sv-benchmarks-test')
    try:
      test_files = glob.glob(os.path.join(self.c_benchmarks_path, '**', '*.c'))
      goto_path = os.path.join(tmpdir, 'out.goto')
      goto_simple_path = os.path.join(tmpdir, 'out-simple.goto')
      for test_file in test_files:
        print('Checking: ' + test_file)
        if test_file in self.test_exclusions:
          result = TestResult.SKIP
        else:
          try:
            self.prepare_c_file(test_file, goto_path, goto_simple_path)
            result = self.run_test(goto_path, goto_simple_path)
          except subprocess.TimeoutExpired:
            result = TestResult.TIMEOUT
          except subprocess.CalledProcessError:
            result = TestResult.ERROR
        print(result.name)
    finally:
      shutil.rmtree(tmpdir)

  def prepare_c_file(self, test_file, goto_path, goto_simple_path):
    self.compile_goto(test_file, out_file=goto_path)
    self.simplify_goto(goto_path, goto_simple_path)
