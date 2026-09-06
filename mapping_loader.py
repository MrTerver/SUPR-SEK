from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
import re

import pandas as pd
import yaml
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string


PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config" / "mappings.yaml"


@dataclass
class LoadResult:
    df: pd.DataFrame
    display_map: dict
    ordered_columns: list
    source_file: str
    sheet_name: str
    warnings: list = field(default_factory=list)
    info: dict = field(default_factory=dict)


def _clean_text(value):
    """
    Приводит значение к строке и убирает пробелы по краям.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _clean_key(value):
    """
    Очищает ключ/номер заявки.

    Например, если из Excel пришло 123.0, делаем 123.
    """

    text = _clean_text(value)
    text = re.sub(r"\.0$", "", text)
    return text


def _is_empty(value):
    """
    Проверяет, является ли значение пустым.
    """

    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == ""

    try:
        return pd.isna(value)
    except TypeError:
        return False


def _to_number(value):
    """
    Пытается превратить значение в число.

    Поддерживает:
    - 123
    - 123.5
    - 123,5
    - 1 234
    - 87%
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return float(value)

    if isinstance(value, (int, float)):
        return float(value)

    text = _clean_text(value)

    if text == "":
        return None

    text = text.replace("\xa0", "")
    text = text.replace(" ", "")
    text = text.replace("%", "")
    text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def _to_date(value):
    """
    Пытается превратить значение в дату.

    Поддерживает:
    - даты из Excel;
    - строки вида 01.09.2026;
    - строки вида 01/09/2026;
    - числа-даты Excel.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return pd.Timestamp(value)

    if isinstance(value, date):
        return pd.Timestamp(value)

    text = _clean_text(value)

    if text == "":
        return None

    # Иногда дата может прийти как числовой серийный номер Excel.
    try:
        num = float(text.replace(",", "."))

        # Примерный диапазон дат Excel: 1950-е - 2100-е годы
        if 20000 < num < 80000:
            return pd.Timestamp("1899-12-30") + pd.Timedelta(days=num)
    except ValueError:
        pass

    parsed = pd.to_datetime(
        text,
        dayfirst=True,
        errors="coerce",
    )

    if pd.isna(parsed):
        return None

    return parsed


def _convert_value(value, type_name):
    """
    Приводит значение к нужному типу из маппинга.
    """

    type_name = (type_name or "text").lower()

    if type_name == "number":
        return _to_number(value)

    if type_name == "date":
        return _to_date(value)

    return _clean_text(value)


def load_mapping_config():
    """
    Читает config/mappings.yaml
    """

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Не найден файл маппинга: {CONFIG_PATH}. "
            f"Создайте файл config/mappings.yaml."
        )

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError(
            f"Файл {CONFIG_PATH} имеет неверную структуру. "
            f"Ожидается словарь с таблицами, например: requests:"
        )

    return config


def _find_source_file(table_config, warnings):
    """
    Ищет исходный файл в папке данных.

    Поддерживает:
    - source_file: точное имя файла;
    - source_file_pattern: маска, например "*.xlsx".
    """

    folder = Path(table_config.get("folder", "data/local"))

    if not folder.is_absolute():
        folder = PROJECT_ROOT / folder

    if not folder.exists():
        raise FileNotFoundError(
            f"Папка с данными не найдена: {folder}. "
            f"Создайте папку data/local и положите туда исходный файл."
        )

    pattern = table_config.get("source_file_pattern")

    if pattern:
        files = list(folder.glob(pattern))

        if not files:
            raise FileNotFoundError(
                f"В папке {folder} не найдены файлы по маске: {pattern}"
            )

        # Берем последний измененный файл
        latest_file = max(files, key=lambda path: path.stat().st_mtime)
        return latest_file

    source_file = table_config.get("source_file")

    if source_file:
        file_path = folder / source_file

        if file_path.exists():
            return file_path

        raise FileNotFoundError(
            f"Файл не найден: {file_path}"
        )

    raise ValueError(
        "В маппинге не указан ни source_file, ни source_file_pattern."
    )


def _get_worksheet(workbook, sheet_name, warnings):
    """
    Возвращает лист из книги Excel.

    Если sheet_name указан и существует — возвращает его.
    Если нет — возвращает первый доступный лист.
    """

    if sheet_name:
        if sheet_name in workbook.sheetnames:
            return workbook[sheet_name], sheet_name

        warnings.append(
            f"Лист '{sheet_name}' не найден. "
            f"Использован первый доступный лист: '{workbook.sheetnames[0]}'."
        )

    active_sheet = workbook.active
    return active_sheet, active_sheet.title


def _build_header_map(worksheet, header_row):
    """
    Собирает заголовки из указанной строки.

    Возвращает словарь:
    номер колонки -> название заголовка
    """

    header_map = {}

    if header_row > worksheet.max_row:
        return header_map

    for cell in worksheet[header_row]:
        header_text = _clean_text(cell.value)

        if header_text:
            header_map[cell.column] = header_text

    return header_map


def _resolve_columns(table_config, header_map, warnings):
    """
    Определяет фактические номера колонок в Excel по настройкам.

    Приоритет:
    1. если указана буква колонки, используем ее;
    2. если буквы нет, ищем колонку по названию заголовка.
    """

    resolved_columns = []

    for column_config in table_config.get("columns", []):
        target = column_config.get("target")

        if not target:
            raise ValueError(
                "В config/mappings.yaml есть колонка без поля target."
            )

        source = column_config.get("source")
        column_letter = column_config.get("column")

        column_index = None

        if column_letter:
            column_letter = str(column_letter).upper()

            try:
                column_index = column_index_from_string(column_letter)
            except Exception as error:
                raise ValueError(
                    f"Некорректная буква колонки '{column_letter}' "
                    f"для поля '{target}'."
                ) from error

            actual_header = header_map.get(column_index)

            if (
                source
                and actual_header
                and actual_header.lower() != source.lower()
            ):
                warnings.append(
                    f"Колонка '{column_letter}': заголовок '{actual_header}' "
                    f"не совпадает с ожидаемым '{source}'."
                )

        elif source:
            for index, header_text in header_map.items():
                if header_text.lower() == source.lower():
                    column_index = index
                    break

            if column_index is None:
                raise ValueError(
                    f"Не найдена колонка с названием '{source}' "
                    f"для поля '{target}'."
                )

        else:
            raise ValueError(
                f"Для поля '{target}' не указаны ни 'column', ни 'source'."
            )

        resolved_columns.append((column_config, column_index))

    return resolved_columns


def load_mapped_table(table_name="requests"):
    """
    Главная функция загрузчика.

    Читает маппинг, находит файл, загружает таблицу
    и возвращает LoadResult.
    """

    warnings = []

    config = load_mapping_config()

    if table_name not in config:
        raise KeyError(
            f"В config/mappings.yaml нет таблицы '{table_name}'. "
            f"Доступны: {', '.join(config.keys())}."
        )

    table_config = config[table_name]

    file_path = _find_source_file(table_config, warnings)

    workbook = load_workbook(
        filename=file_path,
        data_only=True,
    )

    sheet_name_config = table_config.get("sheet_name")
    worksheet, used_sheet_name = _get_worksheet(
        workbook=workbook,
        sheet_name=sheet_name_config,
        warnings=warnings,
    )

    header_row = int(table_config.get("header_row", 1))
    data_start_row = int(table_config.get("data_start_row", header_row + 1))

    header_map = _build_header_map(
        worksheet=worksheet,
        header_row=header_row,
    )

    resolved_columns = _resolve_columns(
        table_config=table_config,
        header_map=header_map,
        warnings=warnings,
    )

    key_column = table_config.get("key_column", "request_number")

    ordered_columns = []
    display_map = {}

    for column_config, _ in resolved_columns:
        target = column_config.get("target")
        ordered_columns.append(target)
        display_map[target] = column_config.get("display") or target

    if key_column not in ordered_columns:
        warnings.append(
            f"Ключевой столбец '{key_column}' "
            f"не найден среди описанных колонок."
        )

    rows = []
    skipped_empty_key = 0

    required_non_key_columns = [
        column_config.get("target")
        for column_config, _ in resolved_columns
        if column_config.get("required") and column_config.get("target") != key_column
    ]

    missing_required_counts = {
        target: 0
        for target in required_non_key_columns
    }

    for row_index in range(data_start_row, worksheet.max_row + 1):
        record = {}
        has_any_value = False

        for column_config, column_index in resolved_columns:
            target = column_config.get("target")
            type_name = column_config.get("type")

            raw_value = worksheet.cell(
                row=row_index,
                column=column_index,
            ).value

            value = _convert_value(raw_value, type_name)

            if target == key_column:
                value = _clean_key(value)

            if not _is_empty(value):
                has_any_value = True

            record[target] = value

        if not has_any_value:
            continue

        if _is_empty(record.get(key_column)):
            skipped_empty_key += 1
            continue

        for target in required_non_key_columns:
            if _is_empty(record.get(target)):
                missing_required_counts[target] += 1

        rows.append(record)

        df = pd.DataFrame(rows, columns=ordered_columns)

    duplicates_count = 0
    duplicate_keys = []
    before_deduplication = len(df)

    if key_column in df.columns:
        duplicated_mask = df.duplicated(subset=[key_column], keep=False)

        duplicate_keys = (
            df.loc[duplicated_mask, key_column]
            .astype(str)
            .unique()
            .tolist()
        )

        df = df.drop_duplicates(subset=[key_column], keep="first")
        duplicates_count = before_deduplication - len(df)

    df = df.reset_index(drop=True)

    if skipped_empty_key:
        warnings.append(
            f"Пропущено строк без номера заявки: {skipped_empty_key}."
        )

    if duplicates_count:
        keys_preview = ", ".join(duplicate_keys[:10])

        warnings.append(
            f"Найдено дублей номеров заявок: {duplicates_count}. "
            f"Номера: {keys_preview}. "
            f"Оставлена первая строка для каждого номера."
        )

    for target, count in missing_required_counts.items():
        if count > 0:
            warnings.append(
                f"Поле '{display_map.get(target, target)}' "
                f"пустое в {count} строках."
            )

    info = {
        "excel_file": str(file_path),
        "sheet_name": used_sheet_name,
        "header_row": header_row,
        "data_start_row": data_start_row,
        "loaded_rows": len(df),
        "skipped_empty_key_rows": skipped_empty_key,
        "duplicates_count": duplicates_count,
        "duplicate_keys": duplicate_keys[:20],
    }

    workbook.close()

    return LoadResult(
        df=df,
        display_map=display_map,
        ordered_columns=ordered_columns,
        source_file=str(file_path),
        sheet_name=used_sheet_name,
        warnings=warnings,
        info=info,
    )


if __name__ == "__main__":
    # Это простая проверка без Streamlit
    result = load_mapped_table("requests")

    print("Файл:", result.source_file)
    print("Лист:", result.sheet_name)
    print("Загружено строк:", len(result.df))
    print()

    if result.warnings:
        print("Предупреждения:")

        for warning in result.warnings:
            print("-", warning)

        print()

    print(result.df.head())