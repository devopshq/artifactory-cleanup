# import inspect
# import os
#
#
# def test_rules_imported():
#     """
#     Проверяем что все правила импортированны в __init__
#     :return:
#     """
#     import policy
#
#     members = inspect.getmembers(policy, inspect.ismodule)
#     modules_imported = set(name for name, _ in members)
#
#     # Берем все файлы с правилами и удаляем .py
#     repo_rules_folder = os.path.dirname(policy.__file__)
#     all_rule_files = set(
#         map(lambda x: x[:-3] if x.endswith(".py") else x, os.listdir(repo_rules_folder))
#     )
#
#     # Удаляем специфичные файлы, которые не надо импортить
#     skip = {
#         "remove_empty_folder",
#         "common",
#         "__init__",
#         "__pycache__",
#     }
#
#     modules = all_rule_files - skip
#
#     not_imported = modules - modules_imported
#     assert len(not_imported) == 0, (
#         "Некоторые модули не импортированы в repo/__init__.py: {}\n"
#         "Импортируйте их в ручную".format(not_imported)
#     )
