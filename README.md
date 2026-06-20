# Проверка GPKG Тобольска по реестру ГИС ЖКХ

## Назначение

Сравнивает данные об управляющих компаниях в `buildings.gpkg` с официальным реестром ГИС ЖКХ и находит изменения.

## Структура

```
work/
├── run_all.py                  ← мастер-скрипт (запускает всё)
├── filter_tobolsk.py           ← этап 1: фильтрация сырых CSV
├── extract_gpkg.py             ← этап 2: извлечение из GPKG
├── compare.py                  ← этап 3: сравнение двух наборов
├── geopackage/
│   └── buildings.gpkg          ← GeoPackage с домами Тобольска
├── tobolsk_houses.csv          ← результат этапа 1 (эталон из ГИС ЖКХ)
├── buildings_houses.csv        ← результат этапа 2 (данные из GPKG)
├── compare_not_found.csv       ← результат этапа 3 (адреса не найденные в ГИС)
├── changes.csv                 ← результат этапа 3 (обнаруженные смены УК)
└── README.md                   ← этот файл
```

## Быстрый запуск

```bash
cd work
python run_all.py
```

Три этапа выполняются последовательно. При ошибке на любом этапе следующие пропускаются.

## Этапы по отдельности

### 1. Фильтрация сырых данных ГИС ЖКХ

```bash
python filter_tobolsk.py
```

**Вход:** CSV-файлы в `../dataset/raw/` (pipe-delimited, кодировка UTF-8)

**Выход:** `tobolsk_houses.csv` — уникальные адреса Тобольска с УК

Из исходных ~1 млн строк (помещений) оставляет только:
- Адреса, содержащие `г. Тобольск`
- Записи с заполненной управляющей компанией

### 2. Извлечение данных из GeoPackage

```bash
python extract_gpkg.py
```

**Вход:** `geopackage/buildings.gpkg`

**Выход:** `buildings_houses.csv` — адреса и УК из GPKG

Читает колонки `addr:city`, `addr:street`, `addr:place`, `addr:housenumber` (адрес) и `management` (УК).

### 3. Сравнение

```bash
python compare.py
```

**Вход:** `tobolsk_houses.csv` (эталон) и `buildings_houses.csv` (проверяемый)

**Выход:**
- `changes.csv` — адреса где УК изменилась: `address`, `old_uk` (GPKG), `new_uk` (ГИС ЖКХ)
- `compare_not_found.csv` — адреса из GPKG, отсутствующие в реестре ГИС ЖКХ

Скрипт нормализует адреса и названия организаций с учётом сокращений из `../сокращения.txt`.

## Обновление данных

1. Добавить новые CSV-файлы ОЖФ в `../dataset/raw/` (автоматически подхватятся)
2. Заменить `geopackage/buildings.gpkg` на актуальную версию
3. Запустить `python run_all.py`

## Зависимости

- Python 3.11+
- pandas
- pyogrio (для чтения GPKG)
