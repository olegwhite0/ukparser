"""
Извлечение адресов и УК из buildings.gpkg в CSV.

Читает buildings.gpkg, строит адрес из OSM-компонент (addr:city, addr:street,
addr:place, addr:housenumber) и берёт management как УК.

Результат: CSV с колонками address и org_name — тот же формат что и tobolsk_houses.csv,
чтобы можно было сравнить два набора.
"""
import os

import pyogrio

# Пути — скрипт лежит в work/, GPKG в корне, результат там же где скрипт
BASE_DIR = os.path.dirname(__file__)
GPKG_PATH = os.path.join(BASE_DIR, "geopackage", "buildings.gpkg")
OUTPUT = os.path.join(BASE_DIR, "buildings_houses.csv")

# Колонки OSM для адреса + management
USECOLS = [
    "addr:city",
    "addr:street",
    "addr:place",
    "addr:housenumber",
    "management",
]


def build_address(city, street, place, housenum):
    """Собрать адресную строку из OSM-компонент."""
    parts = []

    # Регион и город
    region = "Тюменская обл"
    if city and isinstance(city, str) and city.strip():
        parts.append(f"{region}, г. {city.strip()}")
    else:
        parts.append(f"{region}, г. Тобольск")

    # Улица или микрорайон
    if street and isinstance(street, str) and street.strip():
        parts.append(street.strip())
    elif place and isinstance(place, str) and place.strip():
        # Нормализация: "7-й микрорайон" → "микрорайон 7" для сравнения
        parts.append(place.strip())

    # Номер дома
    if housenum:
        # Приводим к строке, убираем .0 если float
        hn = str(housenum).strip()
        if hn.endswith(".0"):
            hn = hn[:-2]
        parts.append(f"д. {hn}")

    return ", ".join(parts)


def main():
    print(f"Чтение {GPKG_PATH}...")
    df = pyogrio.read_dataframe(GPKG_PATH, columns=USECOLS)
    print(f"Всего зданий: {len(df)}")

    # Только здания с заполненным management
    has_mgmt = df["management"].notna() & (df["management"] != "")
    df_mgmt = df[has_mgmt].copy()
    print(f"С management: {len(df_mgmt)}")

    # Строим адрес и чистим название УК
    addresses = []
    org_names = []
    for _, row in df_mgmt.iterrows():
        addr = build_address(
            row.get("addr:city"),
            row.get("addr:street"),
            row.get("addr:place"),
            row.get("addr:housenumber"),
        )
        org = str(row["management"]).strip().strip('"')
        addresses.append(addr)
        org_names.append(org)

    result_data = {"address": addresses, "org_name": org_names}

    import pandas as pd
    result = pd.DataFrame(result_data)
    result = result.sort_values("address").reset_index(drop=True)

    # Сохранение
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\nРезультат сохранён: {OUTPUT}")
    print(f"Строк: {len(result)}")

    # Превью
    org_counts = result["org_name"].value_counts()
    print(f"\nУправляющих компаний: {len(org_counts)}")
    for org, cnt in org_counts.items():
        print(f"  [{cnt} д.] {org[:90]}")

    print(f"\nПримеры адресов:")
    for addr in result["address"].head(5):
        print(f"  {addr}")


if __name__ == "__main__":
    main()
