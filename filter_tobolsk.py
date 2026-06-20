"""
Фильтрация исходных CSV ОЖФ: только дома Тобольска с УК.

Читает pipe-delimited CSV из dataset/raw/, оставляет только записи где:
- Адрес содержит "г. Тобольск" или "г.Тобольск"
- Поле "Наименование организации, осуществляющей управление домом" заполнено

Результат: уникальные адреса с УК, готовые для следующих этапов.
"""
import glob
import os

import pandas as pd

# Пути — скрипт лежит в work/, данные в dataset/raw/, результат там же где скрипт
BASE_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(BASE_DIR, "raw")
OUTPUT = os.path.join(BASE_DIR, "tobolsk_houses.csv")

# Только эти два поля нужны из всего датасета
USECOLS = [
    "Адрес ОЖФ",
    "Наименование организации, осуществляющей управление домом",
]


def is_tobolsk(addr: str) -> bool:
    """Проверка, что адрес относится к городу Тобольск."""
    if not isinstance(addr, str):
        return False
    a = addr.lower()
    return "г. тобольск" in a or "г.тобольск" in a


def main():
    # Поиск всех CSV в raw/
    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))
    if not files:
        print(f"Нет CSV-файлов в {RAW_DIR}")
        return

    print(f"Найдено файлов: {len(files)}")
    for f in files:
        print(f"  {os.path.basename(f)}")

    # Чтение всех файлов, только нужные колонки
    frames = []
    total_rows = 0
    for f in files:
        df = pd.read_csv(
            f,
            delimiter="|",
            usecols=USECOLS,
            dtype=str,
        ).fillna("")
        total_rows += len(df)
        frames.append(df)

    df_all = pd.concat(frames, ignore_index=True)
    print(f"\nВсего строк (помещений): {total_rows}")

    # Фильтр: только Тобольск
    mask_tob = df_all["Адрес ОЖФ"].apply(is_tobolsk)
    print(f"Из них в Тобольске: {mask_tob.sum()}")

    # Фильтр: УК заполнена
    df_tob = df_all[mask_tob].copy()
    df_tob["org_name"] = df_tob[USECOLS[1]].str.strip().str.strip('"').str.replace('""', '"')
    mask_org = df_tob["org_name"] != ""
    print(f"С заполненной УК: {mask_org.sum()}")

    df_filtered = df_tob[mask_org]

    # Агрегация до уникальных адресов (исходные данные — на уровне помещений)
    result = (
        df_filtered
        .groupby("Адрес ОЖФ", sort=False)
        .agg(org_name=("org_name", "first"))
        .reset_index()
    )
    result = result.sort_values("Адрес ОЖФ").reset_index(drop=True)

    print(f"Уникальных адресов: {len(result)}")

    # Сохранение
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\nРезультат сохранён: {OUTPUT}")
    print(f"Колонки: {list(result.columns)}")
    print(f"Строк: {len(result)}")

    # Превью УК
    org_counts = result["org_name"].value_counts()
    print(f"\nУправляющих компаний: {len(org_counts)}")
    for org, cnt in org_counts.head(10).items():
        print(f"  [{cnt} д.] {org[:90]}")
    if len(org_counts) > 10:
        print(f"  ... ещё {len(org_counts) - 10}")


if __name__ == "__main__":
    main()
