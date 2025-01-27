from pathlib import Path
import unittest

import linter


class TestLinter(unittest.TestCase):

    def setUp(self):
        self.test_files = [
            {
                'test_input_file': \
                    Path('test_files', 'test_file_1.py'),
                'test_output_file': \
                    Path('test_files', 'test_file_1_output.py')
            },
            {
                'test_input_file': \
                    Path('test_files', 'test_file_2.py'),
                'test_output_file': \
                    Path('test_files', 'test_file_2_output.py')
            },
            {
                'test_input_file': \
                    Path('test_files', 'test_file_3.py'),
                'test_output_file': \
                    Path('test_files', 'test_file_3_output.py')
            },
            {
                'test_input_file': \
                    Path('test_files', 'test_file_4.py'),
                'test_output_file': \
                    Path('test_files', 'test_file_4_output.py')
            },
            {
                'test_input_file': \
                    Path('test_files', 'test_file_5.py'),
                'test_output_file': \
                    Path('test_files', 'test_file_5_output.py')
            },
            {
                'test_input_file': \
                    Path('test_files', 'test_file_6.py'),
                'test_output_file': \
                    Path('test_files', 'test_file_6_output.py')
            }
        ]

    def test_open_file(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            result = linter.open_file(test_input_file)
            self.assertIsInstance(result, str)

    def test_get_file_lines(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            result = linter.get_file_lines(contents)
            self.assertIsInstance(result, list)

    def test_get_import_lines_with_indices_and_comments(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            file_lines = linter.get_file_lines(contents)
            result = linter.get_import_lines_with_indices_and_comments(
                file_lines
            )
            self.assertIsInstance(result, tuple)

    def test_update_import_lines(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            file_lines = linter.get_file_lines(contents)
            import_lines_with_indices_and_comments, \
                start_index, end_index = \
                linter.get_import_lines_with_indices_and_comments(
                    file_lines
                )
            result = linter.update_import_lines(
                import_lines_with_indices_and_comments
            )
            self.assertIsInstance(result, list)

    def test_update_file_lines(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            file_lines = linter.get_file_lines(contents)
            import_lines_with_indices_and_comments, \
                start_index, end_index = \
                linter.get_import_lines_with_indices_and_comments(
                    file_lines
                )
            updated_import_lines = linter.update_import_lines(
                import_lines_with_indices_and_comments
            )
            result = linter.update_file_lines(
                file_lines,
                updated_import_lines,
                start_index,
                end_index
            )
            self.assertIsInstance(result, list)

    def test_output(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            file_lines = linter.get_file_lines(contents)
            import_lines_with_indices_and_comments, \
                start_index, end_index = \
                linter.get_import_lines_with_indices_and_comments(
                    file_lines
                )
            updated_import_lines = linter.update_import_lines(
                import_lines_with_indices_and_comments
            )
            updated_file_lines = linter.update_file_lines(
                file_lines,
                updated_import_lines,
                start_index,
                end_index
            ) 
            new_file_lines_str = '\n'.join(updated_file_lines)
            test_output_file = test_file['test_output_file']
            with open(test_output_file, 'r', encoding='utf-8') as output_test_file:
                output_test_file_contents = output_test_file.read()
            self.assertEqual(new_file_lines_str, output_test_file_contents)