# create_stub.py
import os
import shutil


def create_stub():
    # Удаляем старую папку, если есть
    stub_dir = "editor_ymaps"
    if os.path.exists(stub_dir):
        shutil.rmtree(stub_dir)

    # Создаём структуру папок
    os.makedirs(os.path.join(stub_dir, "migrations"), exist_ok=True)

    # Создаём файлы с заглушками
    with open(os.path.join(stub_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write('__version__ = "0.0.1"\n')

    with open(os.path.join(stub_dir, "apps.py"), "w", encoding="utf-8") as f:
        f.write('''from django.apps import AppConfig

class EditorYmapsConfig(AppConfig):
    name = 'editor_ymaps'
    verbose_name = 'Editor YMaps'

    def ready(self):
        pass
''')

    with open(os.path.join(stub_dir, "urls.py"), "w", encoding="utf-8") as f:
        f.write('''from django.urls import path

urlpatterns = []
''')

    with open(os.path.join(stub_dir, "models.py"), "w", encoding="utf-8") as f:
        f.write('''from django.db import models
# Пустой файл моделей
''')

    # Пустой файл миграций
    with open(os.path.join(stub_dir, "migrations", "__init__.py"), "w", encoding="utf-8") as f:
        f.write('')

    # Создаём другие возможные файлы
    for filename in ['admin.py', 'forms.py', 'views.py', 'widgets.py']:
        with open(os.path.join(stub_dir, filename), "w", encoding="utf-8") as f:
            f.write(f'# Заглушка для {filename}\n')

    print("✅ Заглушка 'editor_ymaps' создана успешно!")
    print("   Папка: editor_ymaps/")
    print("   Файлы: __init__.py, apps.py, urls.py, models.py и другие")


if __name__ == "__main__":
    create_stub()