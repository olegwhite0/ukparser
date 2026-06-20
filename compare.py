"""
Сравнение данных GPKG с эталоном ГИС ЖКХ.

Проверяет каждый адрес из buildings_houses.csv по tobolsk_houses.csv (эталон).
Нормализует адреса и названия организаций с учётом сокращений из сокращения.txt.

Результат: вывод несовпадений (адрес не найден / разные УК).
"""
import os
import re

import pandas as pd

BASE_DIR = os.path.dirname(__file__)

# Входные файлы
GPKG_CSV = os.path.join(BASE_DIR, "buildings_houses.csv")
GIS_CSV = os.path.join(BASE_DIR, "tobolsk_houses.csv")
ABBREV_FILE = os.path.join(BASE_DIR, "сокращения.txt")

# ===================================================================
# 1. Загрузка сокращений
# ===================================================================

def load_abbreviations(path):
    """Чтение сокращений из файла: полная_форма -> краткая_форма."""
    abbr = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Также"):
                continue
            # Формат: ПОЛНАЯ ФОРМА - краткая
            if " - " in line:
                full, short = line.split(" - ", 1)
                abbr[full.strip()] = short.strip()
            elif " -" in line:
                full, short = line.split(" -", 1)
                abbr[full.strip()] = short.strip()
    return abbr


ABBREVS = load_abbreviations(ABBREV_FILE)
print("Сокращения загружены:")
for full, short in ABBREVS.items():
    print(f"  {full} -> {short}")

# ===================================================================
# 2. Нормализация названий организаций
# ===================================================================

def normalize_org(name: str) -> str:
    """Привести название организации к каноническому виду (краткая форма)."""
    if not isinstance(name, str):
        return ""
    n = name.strip().replace('""', '"')

    # Замена полных форм на краткие
    for full, short in ABBREVS.items():
        # Ищем полную форму в верхнем регистре (как в ГИС ЖКХ)
        n = re.sub(re.escape(full), short, n, flags=re.IGNORECASE)

    # Чистка: убираем кавычки вокруг аббревиатур ("УК " -> УК ")
    for short in ["УК", "УО", "АО", "ТСН"]:
        n = re.sub(rf'"({short})\s+', rf'\1 ', n)

    # Чистка лишних кавычек и пробелов
    n = n.strip()
    # Схлопываем множественные пробелы
    n = re.sub(r"\s+", " ", n)
    # Убираем точку в конце если есть
    n = n.rstrip(".")

    return n


# ===================================================================
# 3. Нормализация адресов
# ===================================================================
# Вместо структурного парсинга — строковая нормализация.
# Оба источника (GPKG и ГИС ЖКХ) прогоняются через одну функцию,
# которая приводит адрес к единому каноническому виду.

# Сокращения: полная форма -> краткая
ABBREV_ADDR = {
    # Типы улиц
    "улица": "ул",
    "проспект": "пр-кт",
    "проезд": "пр-д",
    "переулок": "пер",
    "площадь": "пл",
    "бульвар": "б-р",
    "шоссе": "ш",
    "набережная": "наб",
    "тупик": "туп",
    "тракт": "тракт",
    # Микрорайоны / нас. пункты
    "микрорайон": "мкр",
    "рабочий поселок": "рп",
    "поселок": "пос",
}


def normalize_address(addr: str) -> str:
    """Привести адрес к каноническому ключу для сравнения.

    Шаги:
    1. Убрать индекс, привести к нижнему регистру
    2. Заменить полные формы на краткие (улица->ул, микрорайон->мкр)
    3. Нормализовать номера микрорайонов (10-й мкр -> мкр 10)
    4. Нормализовать корпус/строение (корп.2 -> /2)
    5. Выделить значимую часть: улица/мкр + дом
    """
    if not isinstance(addr, str):
        return ""

    a = addr.strip().lower()

    # 1. Убрать почтовый индекс
    a = re.sub(r"^\d{6}\s*,?\s*", "", a)

    # 2. Заменить полные формы на краткие
    for full, short in ABBREV_ADDR.items():
        a = re.sub(r"\b" + re.escape(full) + r"\b", short, a)

    # 3. Убрать точку после распространённых сокращений
    a = re.sub(r"\b(ул|пер|пр-кт|пр-д|пл|б-р|наб|туп|мкр|рп|пос|г|д|корп|стр)\.", r"\1", a)

    # 4. Нормализовать "корп N" / "стр N" -> "/N"
    a = re.sub(r"корп\s*\.?\s*(\d+)", r"/\1", a)
    a = re.sub(r"стр\s*\.?\s*(\d+)", r"/\1", a)

    # 5. Нормализовать номер микрорайона:
    #    "мкр 10-й" -> "мкр 10", "10-й мкр" -> "мкр 10", "мкр 10а" -> "мкр 10а"
    a = re.sub(r"мкр\s*\.?\s*(\d+[а-яё]?)\s*-?\s*(?:й|[а-яё]+)?", r"мкр \1", a)
    a = re.sub(r"(\d+[а-яё]?)\s*-?\s*(?:й|[а-яё]+)?\s*мкр", r"мкр \1", a)

    # 6. Нормализовать "д N" / "д.N" -> "д N"
    a = re.sub(r"д\s*\.\s*(\d+[а-яё]*)", r"д \1", a)

    # 7. Нормализовать "/ N" -> "/N"
    a = re.sub(r"/\s+(\d+)", r"/\1", a)

    # 8. Выделить часть после "г тобольск"
    m = re.search(r"г\s*\.?\s*тобольск\s*,?\s*(.*)", a)
    if m:
        a = m.group(1).strip()

    # 9. Убрать префиксы (регион, рп)
    a = re.sub(r"тюменская?\s*обл\s*,?\s*", "", a)
    a = re.sub(r"рп\s*\.?\s*", "", a)

    # 10. Финальная чистка
    a = re.sub(r"\s+", " ", a)
    a = re.sub(r",\s*,", ",", a)
    a = a.strip(" ,")

    return a


# ===================================================================
# 4. Сравнение
# ===================================================================

def main():
    print("\n" + "=" * 60)
    print("СРАВНЕНИЕ GPKG vs ГИС ЖКХ")
    print("=" * 60)

    # Загрузка данных
    df_gpkg = pd.read_csv(GPKG_CSV, encoding="utf-8-sig").fillna("")
    df_gis = pd.read_csv(GIS_CSV, encoding="utf-8-sig").fillna("")

    print(f"\nGPKG (проверяемый):  {len(df_gpkg)} адресов")
    print(f"ГИС ЖКХ (эталон):    {len(df_gis)} адресов")

    # Нормализация адресов -> ключи
    df_gpkg["addr_key"] = df_gpkg["address"].apply(normalize_address)
    df_gis["addr_key"] = df_gis["Адрес ОЖФ"].apply(normalize_address)

    # Нормализация названий УК
    df_gpkg["org_norm"] = df_gpkg["org_name"].apply(normalize_org)
    df_gis["org_norm"] = df_gis["org_name"].apply(normalize_org)

    # Строим индекс эталона: addr_key -> org_norm
    gis_index = {}
    for _, row in df_gis.iterrows():
        key = row["addr_key"]
        if key not in gis_index:
            gis_index[key] = []
        gis_index[key].append({
            "org_norm": row["org_norm"],
            "org_orig": row["org_name"],
            "addr_orig": row["Адрес ОЖФ"],
        })

    # Сравнение
    matched = []
    not_found = []
    different_org = []

    for _, row in df_gpkg.iterrows():
        key = row["addr_key"]
        org_gpkg = row["org_norm"]
        addr_gpkg = row["address"]
        org_gpkg_orig = row["org_name"]

        if key not in gis_index:
            not_found.append({
                "gpkg_addr": addr_gpkg,
                "gpkg_key": key,
                "gpkg_org": org_gpkg_orig,
                "gpkg_org_norm": org_gpkg,
            })
            continue

        # Ищем совпадение по организации среди вариантов с этим адресом
        gis_entries = gis_index[key]
        org_matched = False
        best_gis = gis_entries[0]

        for gis_entry in gis_entries:
            # Сравнение: точное и нечёткое
            if org_gpkg.lower() == gis_entry["org_norm"].lower():
                org_matched = True
                best_gis = gis_entry
                break
            # Нечёткое: одно содержит другое
            if org_gpkg.lower() in gis_entry["org_norm"].lower() or \
               gis_entry["org_norm"].lower() in org_gpkg.lower():
                org_matched = True
                best_gis = gis_entry
                break

        if org_matched:
            matched.append({
                "gpkg_addr": addr_gpkg,
                "gis_addr": best_gis["addr_orig"],
                "org": org_gpkg_orig,
            })
        else:
            different_org.append({
                "gpkg_addr": addr_gpkg,
                "gpkg_key": key,
                "gpkg_org": org_gpkg_orig,
                "gpkg_org_norm": org_gpkg,
                "gis_org": best_gis["org_orig"],
                "gis_org_norm": best_gis["org_norm"],
                "gis_addr": best_gis["addr_orig"],
            })

    # ===============================================================
    # 5. Вывод результатов
    # ===============================================================
    print(f"\n{'-' * 60}")
    print("РЕЗУЛЬТАТЫ")
    print(f"{'-' * 60}")
    print(f"  Совпало (адрес + УК):   {len(matched)}")
    print(f"  Адрес не найден в ГИС:  {len(not_found)}")
    print(f"  Разные УК:              {len(different_org)}")

    if not_found:
        print(f"\n{'-' * 60}")
        print(f"АДРЕСА НЕ НАЙДЕННЫЕ В ГИС ЖКХ ({len(not_found)}):")
        print(f"{'-' * 60}")
        for i, item in enumerate(not_found, 1):
            print(f"\n{i}. GPKG: {item['gpkg_addr']}")
            print(f"   Ключ: {item['gpkg_key']}")
            print(f"   УК:   {item['gpkg_org']}")

    if different_org:
        print(f"\n{'-' * 60}")
        print(f"ИЗМЕНЕНИЯ УПРАВЛЯЮЩИХ КОМПАНИЙ ({len(different_org)}):")
        print(f"{'-' * 60}")
        for i, item in enumerate(different_org, 1):
            print(f"\n{i}. {item['gpkg_addr']}")
            print(f"   Было (GPKG):  {item['gpkg_org']}")
            print(f"   Стало (ГИС):  {item['gis_org']}")

        # Сохраняем изменения в удобном формате
        changes = []
        for item in different_org:
            changes.append({
                "address": item["gpkg_addr"],
                "old_uk": item["gpkg_org"],
                "new_uk": item["gis_org"],
            })
        changes_path = os.path.join(BASE_DIR, "changes.csv")
        pd.DataFrame(changes).to_csv(changes_path, index=False, encoding="utf-8-sig")
        print(f"\n  Список изменений сохранён: changes.csv")
    else:
        print(f"\n{'-' * 60}")
        print("ИЗМЕНЕНИЙ УПРАВЛЯЮЩИХ КОМПАНИЙ НЕТ")
        print(f"{'-' * 60}")
        print("  Все адреса в GPKG совпадают с реестром ГИС ЖКХ.")

    # Сохраняем детальные отчёты (предварительно чистим старые)
    not_found_path = os.path.join(BASE_DIR, "compare_not_found.csv")
    diff_org_path = os.path.join(BASE_DIR, "compare_diff_org.csv")

    # Удаляем старые файлы чтобы не оставалось данных от прошлых прогонов
    for p in [not_found_path, diff_org_path]:
        if os.path.exists(p):
            os.remove(p)

    # Пишем только если есть данные
    pd.DataFrame(not_found).to_csv(not_found_path, index=False, encoding="utf-8-sig")
    print(f"\nДетали сохранены: compare_not_found.csv ({len(not_found)} записей)")

    if different_org:
        pd.DataFrame(different_org).to_csv(diff_org_path, index=False, encoding="utf-8-sig")
        print(f"Детали сохранены: compare_diff_org.csv ({len(different_org)} записей)")
    else:
        print("Различий в УК не найдено")


if __name__ == "__main__":
    main()
