"""
Мастер-скрипт: полный цикл проверки GPKG по эталону ГИС ЖКХ.

Этапы:
  1. filter_tobolsk  — фильтрация исходных CSV ОЖФ (dataset/raw/ -> tobolsk_houses.csv)
  2. extract_gpkg    — извлечение адресов из buildings.gpkg (-> buildings_houses.csv)
  3. compare         — сравнение GPKG с эталоном ГИС ЖКХ

Использование: python run_all.py
"""
import os
import subprocess
import sys
import time

WORK_DIR = os.path.dirname(__file__)

STAGES = [
    {
        "name": "Фильтрация ОЖФ (ГИС ЖКХ)",
        "script": "filter_tobolsk.py",
        "produces": "tobolsk_houses.csv",
        "desc": "Чтение dataset/raw/*.csv -> только Тобольск + УК",
    },
    {
        "name": "Извлечение из GPKG",
        "script": "extract_gpkg.py",
        "produces": "buildings_houses.csv",
        "desc": "Чтение buildings.gpkg -> адреса + management",
    },
    {
        "name": "Сравнение GPKG vs ГИС ЖКХ",
        "script": "compare.py",
        "produces": ["compare_not_found.csv", "compare_diff_org.csv"],
        "desc": "Проверка каждого адреса GPKG по эталону",
    },
]


def run_stage(script_name):
    """Запустить скрипт этапа, вернуть (success, output_lines)."""
    script_path = os.path.join(WORK_DIR, script_name)

    if not os.path.exists(script_path):
        print(f"  [ОШИБКА] Скрипт не найден: {script_path}")
        return False, []

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=WORK_DIR,
        )
        output = result.stdout.splitlines()
        if result.returncode != 0:
            print(f"  [ОШИБКА] Скрипт завершился с кодом {result.returncode}")
            for line in result.stderr.splitlines()[-5:]:
                print(f"    {line}")
            return False, output
        return True, output
    except subprocess.TimeoutExpired:
        print(f"  [ОШИБКА] Превышено время ожидания (10 мин)")
        return False, []
    except Exception as e:
        print(f"  [ОШИБКА] {e}")
        return False, []


def extract_stats(output_lines):
    """Извлечь ключевые цифры из вывода скрипта."""
    stats = {}
    for line in output_lines:
        line = line.strip()
        if ":" in line and not line.startswith("=") and not line.startswith("-"):
            # Ищем паттерны вроде "Всего строк: 12345" или "Уникальных адресов: 564"
            pass
    return stats


def print_separator(char="=", width=60):
    print(char * width)


def main():
    print_separator()
    print("  ПРОВЕРКА GPKG ТОБОЛЬСКА ПО РЕЕСТРУ ГИС ЖКХ")
    print_separator()

    start_time = time.time()
    all_ok = True

    for i, stage in enumerate(STAGES, 1):
        print(f"\n  Этап {i}/{len(STAGES)}: {stage['name']}")
        print(f"  {stage['desc']}")
        print(f"  Запуск {stage['script']}...")

        ok, output = run_stage(stage["script"])
        if not ok:
            all_ok = False
            print(f"\n  [!] Этап '{stage['name']}' не выполнен. Дальнейшие этапы пропущены.")
            break

        # Показываем ключевые строки вывода
        important = [l for l in output if l.strip() and not l.startswith("Сокращения")]
        for line in important[:12]:
            print(f"    {line}")
        if len(important) > 12:
            print(f"    ... (ещё {len(important) - 12} строк)")

        # Проверяем, что выходной файл создан
        produces = stage["produces"]
        if isinstance(produces, str):
            produces = [produces]
        for fname in produces:
            fpath = os.path.join(WORK_DIR, fname)
            if os.path.exists(fpath):
                size_kb = os.path.getsize(fpath) / 1024
                print(f"    -> {fname} ({size_kb:.1f} КБ)")
            else:
                print(f"    [!] {fname} не создан")

    # Итоги
    elapsed = time.time() - start_time
    print(f"\n")
    print_separator()
    if all_ok:
        print("  ВСЕ ЭТАПЫ ВЫПОЛНЕНЫ УСПЕШНО")
    else:
        print("  ВЫПОЛНЕНИЕ ПРЕРВАНО — не все этапы завершены")
    print(f"  Время: {elapsed:.1f} сек")
    print_separator()

    # Итоговые файлы
    print("\n  Результаты:")
    for fname in ["tobolsk_houses.csv", "buildings_houses.csv",
                  "compare_not_found.csv", "changes.csv"]:
        fpath = os.path.join(WORK_DIR, fname)
        if os.path.exists(fpath):
            size_kb = os.path.getsize(fpath) / 1024
            print(f"    {fname} ({size_kb:.1f} КБ)")

    # Краткая сводка сравнения
    import pandas as pd
    not_found_path = os.path.join(WORK_DIR, "compare_not_found.csv")
    changes_path = os.path.join(WORK_DIR, "changes.csv")

    nf_count = 0
    ch_count = 0
    if os.path.exists(not_found_path) and os.path.getsize(not_found_path) > 10:
        nf_count = len(pd.read_csv(not_found_path))
    if os.path.exists(changes_path) and os.path.getsize(changes_path) > 10:
        ch_df = pd.read_csv(changes_path)
        ch_count = len(ch_df)
        print(f"\n  >>> НАЙДЕНЫ ИЗМЕНЕНИЯ УК ({ch_count} адресов)! <<<")
        for i, (_, c) in enumerate(ch_df.iterrows(), 1):
            print(f"  {i}. {c['address']}")
            print(f"     Было (GPKG):  {c['old_uk']}")
            print(f"     Стало (ГИС):  {c['new_uk']}")
        print(f"\n  Подробности в: work/changes.csv")

    print(f"\n  Сводка сравнения:")
    print(f"    Адресов не найдено в ГИС: {nf_count}")
    print(f"    Смен УК: {ch_count}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
