from argparse import ArgumentParser
import importlib.util
import logging
from logging import LogRecord
import os
from pathlib import Path
import re
import sys

# Создаём класс для присваивания цветов логам
class ColourFormatter(logging.Formatter):
    COLOURS = {
         'INFO': '\033[32m',
         'WARNING': '\033[33m',
         'ERROR': '\033[31m'
    }
    RESET = '\033[0m'

    def format(self, record: LogRecord) -> str:
        log_color = self.COLOURS.get(record.levelname, self.RESET)
        record.msg = f'{log_color}{record.msg}{self.RESET}'
        return super().format(record)


# Выставляются настройки логирования
logger = logging.getLogger('linter')
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
formatter = ColourFormatter('%(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# Добавляется CLI
# Происходит разбор заданных аргументов
parser = ArgumentParser(
    prog='Linter',
    description='Simple Python linter'
)
parser.add_argument('filepath')
parser.add_argument(
    '-i', 
    '--imports',
    default=False, 
    action='store_true',
    help='Реорганизация импортов'
)
parser.add_argument(
    '-ll',
    '--lines_lengths',
    const=79,
    nargs='?',
    action='store',
    help='Проверка длины строк. Можно указать максимально допустимое '
    'значение (по умолчанию 79). Будут выданы строки с длиной, которая '
    'превышает указанное значение'
)
args = parser.parse_args()


def open_file(filepath: str | Path) -> str:
    '''
    Возвращает содержимое файла
    '''
    if not str(filepath).endswith('.py'):
        logger.warning(f'Не ".py" расширение файла: {filepath}')
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            contents = file.read()
            return contents
    except FileNotFoundError:
        logger.error(f'Неправильный путь к файлу: {filepath}')
        sys.exit()


def get_file_lines(contents: str) -> list:
    '''
    Возвращает список строк содержимого
    '''
    return contents.splitlines()


def check_lines_lenghts(
    file_lines: list,
    max_length: int = 79 # Согласно PEP8, максимально допустимая длина строки
) -> None:
    '''
    Проверяет длину строк
    '''
    logger.info(
        'Проверка, есть ли строки, которые '
        f'содержат более {max_length} знаков'
    )
    for idx, line in enumerate(file_lines):        
        if len(line) > max_length:
            logger.error(
                f'Строка {idx + 1}: "{line.lstrip()[:50]}..." '
            )


def get_import_lines_with_indices_and_comments(
        file_lines: list
    ) -> tuple | None:
    '''
    Возвращает список словарей, где каждый словарь содержит строку импорта, 
    соответствующие этой строке комментарии (кроме строчных комментариев), 
    все комментарии выше строки импорта до предыдущего импорта считаются 
    комментариями нижестоящего импорта. Также словарь содержит номер строки 
    импорта в изначальном файле. Возвращает начальный и конечный индексы 
    раздела импортов в списке строк содержимого
    '''
    import_lines = []
    start_index = _get_import_section_start_index(file_lines)
    if not isinstance(start_index, int):
        return
    end_index = _get_import_section_end_index(file_lines)
    # Выделяем раздел импортов
    import_section = file_lines[start_index:end_index]
    
    # Создаём список словарей с импортами и номерами строк этих импортов, 
    # а также комментариями к этим импортам
    def get_full_line_commentaries(line_index: int) -> list:
        commentaries = []
        count = 0
        while True:
            count += 1
            line_above_import = import_section[line_index - count].strip()
            if line_above_import.startswith('#'):
                commentaries.append(line_above_import)
            elif line_above_import == '':
                continue
            else:
                break
        return commentaries[::-1]
        
    import_lines = [
        {
            'import_line': line,
            'line_index': idx + 1,
            'full_line_commentaries': get_full_line_commentaries(idx)
        } for idx, line in enumerate(import_section) \
            if line.strip() != '' and not line.strip().startswith('#')
    ]
    return import_lines, start_index, end_index


def update_import_lines(import_lines: list) -> list:
    '''
    Проверяет наличие повторяющихся импортов и 
    обновляет раздел импортов, если повторений нет
    '''
    # Переводим строки раздела импортов в удобный формат
    imports_dicts = _get_imports_dicts_detailed(import_lines)
    # Проверяем наличие дубликатов
    _check_duplicates(imports_dicts)
    # Меняем порядок импортов для его соответствия PEP8
    updated_import_lines = _reorganize_order(
        imports_dicts
    )
    return updated_import_lines


def update_file_lines(
    file_lines: list,
    new_lines: list,
    file_lines_start_index: int,
    file_lines_end_index: int
) -> list:
    '''
    Обновляет исходные данные файла
    '''
    file_lines[file_lines_start_index:file_lines_end_index] = new_lines
    updated_code_start_index = file_lines_start_index
    updated_code_end_index = file_lines_start_index + len(new_lines)
    file_lines = _add_spacing(
        file_lines,
        updated_code_start_index,
        updated_code_end_index
    )
    return file_lines


def update_file(filepath: str, new_file_lines: list) -> None:
    '''
    Обновляет заданный файл
    '''
    new_file_lines_str = '\n'.join(new_file_lines)
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(new_file_lines_str)


def _add_spacing(
        file_lines: list,
        updated_code_start_index: int,
        updated_code_end_index: int
    ) -> list:
    '''
    Возвращает строки раздела импортов с правильным отступом после него
    '''
    # Ставим необходимые пустые строки после раздела импортов
    empty_lines_after_imports = 0
    for idx, line in enumerate(file_lines[updated_code_end_index:]):
        if line.strip() == '':
            empty_lines_after_imports += 1
        else:
            if line.startswith('#') or \
                line.startswith('"""') or \
                line.startswith("'''"):
                if not empty_lines_after_imports:
                    file_lines.insert(
                        updated_code_end_index,
                        ''
                    )
                elif empty_lines_after_imports > 1:
                    for _ in range(empty_lines_after_imports - 1):
                        file_lines.pop(updated_code_end_index)
                break
            else:
                if empty_lines_after_imports < 2:
                    for _ in range(2 - empty_lines_after_imports):
                        file_lines.insert(
                            updated_code_end_index,
                            ''
                        )
                elif empty_lines_after_imports > 2:
                    for _ in range(empty_lines_after_imports - 2):
                        file_lines.pop(updated_code_end_index)
                break
    # Ставим необходимый отступ (если необходимо) перед разделом импортов
    empty_lines_before_first_import = 0
    for line in reversed(file_lines[:updated_code_start_index]):
        if line.strip() != '':
            break
        else:
            empty_lines_before_first_import += 1
    if empty_lines_before_first_import > 1:
        # Оставляем одну пустую строку, если их несколько
        for _ in range(empty_lines_before_first_import-1):
            file_lines.pop(
                updated_code_start_index-empty_lines_before_first_import
            )
    return file_lines


def _get_import_section_start_index(file_lines: list) -> int | None:
    '''
    Возвращает индекс начала раздела импортов или ничего, если импортов нет
    '''
    # Определяем, где начинается раздел импортов 
    # Если перед первым импортом несколько пустых строк, то считаем началом  
    # вторую пустую строку (для последующего удаления лишних)
    for idx, line in enumerate(file_lines):
        if line.startswith('import') or line.startswith('from'):
            start_index = idx
            break
    if not 'start_index' in locals():
        return
    return start_index


def _get_import_section_end_index(file_lines: list) -> int:
    '''
    Возвращает индекс конца раздела импортов (добавляется один к
    значению для корректного слайсинга)
    '''
    for idx, line in enumerate(file_lines):
        if not line.startswith('import') and \
            not line.startswith('from') and \
            not line.startswith('#') and \
            not line.strip() == '':
            other_section_start_index = idx
            break
        if line.startswith('#'):
            comment_index = idx
            lines_after_comment = file_lines[comment_index:]
            break_main_loop = False
            for line in lines_after_comment:
                if line.startswith('import') or \
                    line.startswith('from'):
                    break
                elif line.startswith('#') or \
                    line.strip() == '':
                    continue
                else:
                    other_section_start_index = comment_index
                    break_main_loop = True
                    break
            if break_main_loop:
                break
    for idx, line in enumerate(reversed(
        file_lines[:other_section_start_index]
    )):
        if line.startswith('import') or \
            line.startswith('from'):
            end_index = other_section_start_index - idx
            break
    return end_index


def _get_imports_dicts_detailed(
    import_lines_with_indices_and_comments: list
) -> list:
    '''
    Переводит список словарей с импортами, номерами строк этих импортов и 
    комментариями в формат списка словарей, где каждый словарь содержит 
    изначальную строку импорта, ее номер в файле, сгенерированную строку 
    импорта (когда исходная строка импорта содержит одновременную загрузку 
    нескольких верхнеуровневых модулей, она разбивается на несколько строк, а 
    каждый сгенерированный словарь соответствует одной строке импорта), 
    название выгружаемого верхнеуровневого модуля, список словарей 
    импортируемых элементов (элемент и псевдоним, если таковой есть)
    '''
    imports_dicts_detailed = []
    regex_pattern = _get_import_string_regex()
    for idx, import_line_with_index_and_comment \
        in enumerate(import_lines_with_indices_and_comments):
        line = import_line_with_index_and_comment['import_line']
        line_index = import_line_with_index_and_comment['line_index']
        import_string_match = re.match(
            regex_pattern,
            line
        )
        if import_string_match:
            module = import_string_match.group('module')
            module_alias = import_string_match.group('module_alias')
            another_module = import_string_match.group('another_module')
            module_var2 = import_string_match.group('module_var2')
            inline_comment = import_string_match.group('inline_comment')
            if inline_comment:
                spaces_before_inline_comment = 0
                for char in inline_comment:
                    if char == ' ':
                        spaces_before_inline_comment += 1
                    else:
                        if spaces_before_inline_comment != 2:
                            formatted_inline_comment = '  ' + \
                                inline_comment[spaces_before_inline_comment:]                            
                        else:
                            formatted_inline_comment = inline_comment
                        break
                # Проверяем, если стоит только один хэштэг
                number_of_hashtags = 0
                for char in formatted_inline_comment[3:]:
                    if char == '#':
                        number_of_hashtags += 1
                    else:
                        formatted_inline_comment = \
                            formatted_inline_comment[:3] + \
                            formatted_inline_comment[
                                (3 + number_of_hashtags):
                            ]
                        break
                # Ставим нужное кол-во пробелов между знаком "#" и 
                # текстом комментария
                spaces_before_comment_text = 0                
                for char in formatted_inline_comment[3:]:
                    if char == ' ':
                        spaces_before_comment_text += 1
                    else:
                        formatted_inline_comment = \
                            formatted_inline_comment[:3] + ' ' + \
                            formatted_inline_comment[
                                (3 + spaces_before_comment_text):
                            ]
                        break
            full_line_commentaries = \
                import_line_with_index_and_comment['full_line_commentaries']
            if another_module:
                modules_str = line.split('import ')[1]
                if inline_comment:
                    modules_with_aliases = modules_str[
                        :-(len(inline_comment))
                    ].split(', ')
                else:
                    modules_with_aliases = modules_str.split(', ')
                for idx, module_with_alias in enumerate(modules_with_aliases):
                    if inline_comment:
                        new_line = 'import ' + module_with_alias + \
                            formatted_inline_comment
                    else:
                        new_line = 'import ' + module_with_alias
                    try:
                        import_full_name, import_alias = \
                        module_with_alias.split(' as ')
                    except ValueError:
                        import_full_name = module_with_alias
                        import_alias = None
                    module_name = import_full_name.split('.')[0]
                    import_name = import_full_name.split('.')[-1]
                    imports_dicts_detailed.append({
                        'initial_string': line,
                        'initial_string_index': line_index,
                        'import_string': new_line,
                        'module_name': module_name,
                        'full_line_commentaries': full_line_commentaries \
                            if idx == 0 else None,
                        'import': [
                            {
                                'import_name': import_name,
                                'import_alias': import_alias
                            }
                        ]
                    })
                continue
            elif module:
                module_name = module.split('.')[0]
                imported = [
                    {
                        'import_name': module.split('.')[-1],
                        'import_alias': module_alias
                    }
                ]
            elif module_var2:
                module_name = module_var2.split('.')[0]
                imports_str = line.split('import ')[1]
                imports_with_aliases = imports_str.split(', ')
                imported = []
                for import_with_alias in imports_with_aliases:
                    try:
                        import_full_name, import_alias = \
                        import_with_alias.split(' as ')
                    except ValueError:
                        import_full_name = import_with_alias
                        import_alias = None
                    import_name = import_full_name.split('.')[-1]
                    imported.append(
                        {
                            'import_name': import_name,
                            'import_alias': import_alias
                        }
                    )        
            if inline_comment:
                new_line = line.replace(
                    inline_comment,
                    formatted_inline_comment
                )
            else:
                new_line = line
            imports_dicts_detailed.append({
                'initial_string': line,
                'initial_string_index': line_index,
                'import_string': new_line,
                'module_name': module_name,
                'full_line_commentaries': full_line_commentaries,
                'import': imported
            })
        else:
            logger.error(
                f'Ошибка в строке: "{line}". '
                'Исправьте ошибку и перезапустите скрипт'
            )
            sys.exit()
    return imports_dicts_detailed


def _get_import_string_regex() -> str:
    '''
    Возвращает regex-шаблон строки раздела импортов
    '''
    return r'(^import\s(?P<module>\w+(\.\w+)*)' \
        r'(?:\sas\s(?P<module_alias>\w+))?' \
        r'(, (?P<another_module>\w+(\.\w+)*)' \
        r'(?:\sas\s(?P<another_module_alias>\w+))?)*|' \
        r'(?:^from\s(\.|\.{2})?(?P<module_var2>\w+(\.\w+)*)\s' \
        r'import\s(?P<subentity>(\w+|\*))' \
        r'(?:\sas\s(?P<subentity_alias>\w+))?' \
        r'(\,\s(?P<another_subentity>\w+)' \
        r'(?:\sas\s(?P<another_subentity_alias>\w+))?)*))' \
        r'(?P<inline_comment>(\s+)?\#.+)?$'


def _check_duplicates(imports_dicts: list) -> None:
    '''
    Проверяет наличие повторяющихся импортов
    '''
    imports_dicts_wo_dp_lns = []
    for import_dict in imports_dicts:
        if import_dict not in imports_dicts_wo_dp_lns:
            imports_dicts_wo_dp_lns.append(import_dict)
        else:
            logger.error(
                'Найден повторный импорт в строке '
                f'{import_dict['initial_string_index']}: '
                f'"{import_dict['initial_string']}", '
                'исправьте проблему и перезапустите скрипт'
            )
            sys.exit()
    imports_names = set()
    imports_aliases = set()
    for import_dict in imports_dicts_wo_dp_lns:
        ln_imports_names_with_aliases = [
            imp for imp in import_dict['import']
        ]
        for import_name_with_alias in ln_imports_names_with_aliases:
            import_name = import_name_with_alias['import_name']
            import_alias = import_name_with_alias['import_alias']
            if import_name not in imports_names:
                imports_names.add(import_name)
            else:
                logger.error(
                    'Найден повторный импорт в строке '
                    f'{import_dict['initial_string_index']}: '
                    f'"{import_dict['initial_string']}", '
                    'исправьте проблему и перезапустите скрипт'
                )
                sys.exit()
            if import_alias and import_alias not in imports_aliases:
                imports_aliases.add(import_alias)
            elif import_alias:
                logger.error(
                    'Найден повторный псевдоним в строке '
                    f'{import_dict['initial_string_index']}: '
                    f'"{import_dict['initial_string']}", '
                    'исправьте проблему и перезапустите скрипт'
                )
                sys.exit()


def _reorganize_order(imports_dicts_detailed: list) -> list:
    '''
    Реорганизует раздел импортов согласно PEP8

    Для того, чтобы корректно отразились сторонние модули, 
    они должны быть установлены. Если используется виртуальная 
    среда, она должна быть активирована
    '''
    standard_and_builtin = []
    third_party = []
    local = []
    for import_dict in imports_dicts_detailed:
        imported_module_name = import_dict['module_name']
        if imported_module_name in sys.stdlib_module_names or \
            imported_module_name in sys.builtin_module_names:
            standard_and_builtin.append(import_dict)
        else:
            spec = importlib.util.find_spec(imported_module_name)
            if spec and spec.origin:
                is_third_party = False
                module_path = os.path.abspath(spec.origin)
                for site_package_path in sys.path:
                    if 'site-packages' in site_package_path and \
                    module_path.startswith(site_package_path):
                        is_third_party = True
                        break
                if is_third_party:
                    third_party.append(import_dict)
                else:
                    local.append(import_dict)
            else:
                local.append(import_dict)
    imports_groups = []
    for imports_group in (standard_and_builtin, third_party, local):
        if imports_group:
            # Сортируем в алфавитном порядке каждую группу импортов
            imports_group_sorted_items = []
            # Сортировка выгружаемых элементов, если строка содержит 
            # больше одного выгружаемого элемента
            imports_group_sorted_subitems = []
            for imports_group_import in imports_group:
                if len(imports_group_import['import']) > 1:
                    imports_group_import['import'] = sorted(
                        imports_group_import['import'],
                        key=lambda x: x['import_name']
                    )
                    imports_group_import_sorted_items = [
                        imp['import_name'] for imp in \
                            imports_group_import['import']
                    ] 
                    imports_group_import['import_string'] = \
                        'from ' + imports_group_import['module_name'] + ' ' \
                            'import ' + ', '.join(
                                imports_group_import_sorted_items
                            )
                imports_group_sorted_subitems.append(
                    imports_group_import
                )
            imports_groups_sorted = sorted(
                imports_group_sorted_subitems,
                key=lambda x: (
                    x['module_name'],
                    'from' in x.get('initial_string'),
                    x['import'][0]['import_name']
                )
            )
            imports_groups.append(imports_groups_sorted)
    reorganized_imports = []
    for idx, imports_group in enumerate(imports_groups):
        for imp in imports_group:
            if imp['full_line_commentaries']:
                reorganized_imports.extend(imp['full_line_commentaries'])
            reorganized_imports.append(imp['import_string'])
        if idx != len(imports_groups) - 1:
            # Разделение различных групп раздела импортов
            # пустыми строками
            reorganized_imports.append('')
    return reorganized_imports


if __name__ == '__main__':
    file_contents = open_file(args.filepath)
    file_lines = get_file_lines(file_contents)
    if args.lines_lengths:
        max_line_length = int(args.lines_lengths)
        check_lines_lenghts(file_lines, max_line_length)
    if args.imports:
        import_lines_with_indices_and_comments = \
            get_import_lines_with_indices_and_comments(file_lines)
        if import_lines_with_indices_and_comments:
            import_lines_to_update, start_index, end_index = \
            import_lines_with_indices_and_comments
        else:
            logger.warning('Раздела импортов не обнаружено')
            sys.exit()
        updated_import_lines = update_import_lines(
            import_lines_to_update
        )
        updated_file_lines = update_file_lines(
            file_lines,
            updated_import_lines,
            start_index,
            end_index
        )
        update_file(args.filepath, updated_file_lines)