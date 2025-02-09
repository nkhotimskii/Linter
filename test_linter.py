import os
import unittest

import linter


class TestLinter(unittest.TestCase):

    def setUp(self):
        test_files_directory = 'tests'
        self.test_files = []
        for subdirectory in os.listdir(test_files_directory):
            test_files_names = os.listdir(os.path.join(
                test_files_directory,
                subdirectory
            ))
            for test_file_name in test_files_names:
                if not test_file_name.endswith('output'):
                    file_name_without_extension = test_file_name.split('.py')[0]
                    for test_file_name_to_compare in test_files_names:
                        file_name_without_extension_to_compare = \
                            test_file_name_to_compare.split('.py')[0]
                        if file_name_without_extension + '_output' == \
                            file_name_without_extension_to_compare:
                            self.test_files.append(
                                {
                                    'test_input_file': os.path.join(
                                        test_files_directory, 
                                        subdirectory,
                                        test_file_name
                                    ),
                                    'test_output_file': os.path.join(
                                        test_files_directory,
                                        subdirectory, 
                                        test_file_name_to_compare
                                    )
                                }
                            )

    def test_open_file(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            result = linter.open_file(test_input_file)
            self.assertIsInstance(result, str)

    def test_get_file_lines(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            code = linter.Code(contents)
            result = code.initial_lines
            self.assertIsInstance(result, list)

    def test_get_import_lines_with_indices_and_comments(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            code = linter.Code(contents)
            file_lines = code.initial_lines
            result = linter.get_import_lines_with_indices_and_comments(
                file_lines
            )
            self.assertIsInstance(result, tuple | None)

    def test_update_import_lines(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            code = linter.Code(contents)
            file_lines = code.initial_lines       
            import_lines_with_indices_and_comments = \
                linter.get_import_lines_with_indices_and_comments(
                    file_lines
                )
            if import_lines_with_indices_and_comments:
                import_lines_to_update, start_index, end_index = \
                import_lines_with_indices_and_comments
            else:
                return
            result = linter.update_import_lines(
                import_lines_to_update
            )
            self.assertIsInstance(result, list)

    def test_update_file_lines(self):
        for test_file in self.test_files:
            test_input_file = test_file['test_input_file']
            contents = linter.open_file(test_input_file)
            code = linter.Code(contents)
            file_lines = code.initial_lines
            import_lines_with_indices_and_comments = \
                linter.get_import_lines_with_indices_and_comments(
                    file_lines
                )
            if import_lines_with_indices_and_comments:
                import_lines_to_update, start_index, end_index = \
                import_lines_with_indices_and_comments
            else:
                return
            updated_import_lines = linter.update_import_lines(
                import_lines_to_update
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
            code = linter.Code(contents)
            file_lines = code.initial_lines
            import_lines_with_indices_and_comments = \
                linter.get_import_lines_with_indices_and_comments(
                    file_lines
                )
            if import_lines_with_indices_and_comments:
                import_lines_to_update, start_index, end_index = \
                import_lines_with_indices_and_comments
            else:
                return
            updated_import_lines = linter.update_import_lines(
                import_lines_to_update
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