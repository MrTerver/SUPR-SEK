from pathlib import Path
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent / "data" / "local"
KEY_COLUMN = "request_number"

# Варианты названий столбца с номером заявки, которые мы понимаем
KEY_ALIASES = [
    KEY_COLUMN,
    "request_id",
    "request",
    "заявка",
    "номер заявки",
    "№ заявки",
    "номер_заявки",
    "№_заявки",
    "№заявки",
]


def _find_data_file(base_name: str):
    """
    Ищет файл в папке data/local.

    Приоритет:
    1. CSV
    2. XLSX

    Если есть оба файла, используется CSV.
    """

    csv_path = DATA_DIR / f"{base_name}.csv"
    xlsx_path = DATA_DIR / f"{base_name}.xlsx"

    if csv_path.exists():
        return csv_path, "csv"

    if xlsx_path.exists():
        return xlsx_path, "xlsx"

    return None, None


def _read_table(base_name: str):
    """
    Читает таблицу из CSV или XLSX.

    Все значения читаем как текст, чтобы избежать проблем,
    когда Excel хранит числа как текст или наоборот.
    """

    path, file_type = _find_data_file(base_name)

    if path is None:
        return pd.DataFrame()

    if file_type == "csv":
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    else:
        # Пока читаем первый лист.
        # Если позже нужно будет читать конкретный лист, добавим настройку.
        df = pd.read_excel(path, dtype=str)

    # Удаляем полностью пустые строки
    df = df.dropna(how="all")

    # Приводим названия столбцов к строке и убираем лишние пробелы
    df.columns = [str(column).strip() for column in df.columns]

    # Приводим все значения к строке и убираем пробелы по краям
    for column in df.columns:
        df[column] = df[column].astype("string").str.strip().fillna("")

    return df


def _clean_key_values(series: pd.Series):
    """
    Чистит значения ключа/номера заявки.

    Например, если Excel прочитал число как 123.0,
    делаем из него 123.
    """

    series = series.astype("string").str.strip().fillna("")

    # Убираем хвост .0 у значений вида "123.0"
    series = series.str.replace(r"\.0$", "", regex=True)

    return series


def _ensure_key_column(df: pd.DataFrame, file_description: str):
    """
    Ищет столбец с номером заявки и переименовывает его
    во внутренний столбец request_number.
    """

    if df.empty:
        return df

    lower_to_original = {
        str(column).lower(): column
        for column in df.columns
    }

    # Сначала ищем точное совпадение из списка алиасов
    for alias in KEY_ALIASES:
        original_column = lower_to_original.get(alias.lower())

        if original_column is not None:
            df = df.rename(columns={original_column: KEY_COLUMN})
            df[KEY_COLUMN] = _clean_key_values(df[KEY_COLUMN])
            return df

    # Если точного совпадения нет, ищем столбец,
    # который содержит слова "заявк" и "номер" или символ "№"
    for original_column in df.columns:
        low = str(original_column).lower()

        if "заявк" in low and ("номер" in low or "№" in low):
            df = df.rename(columns={original_column: KEY_COLUMN})
            df[KEY_COLUMN] = _clean_key_values(df[KEY_COLUMN])
            return df

    raise ValueError(
        f"В файле {file_description} не найден столбец с номером заявки. "
        f"Назовите его, например, '№ заявки', 'Номер заявки' или 'request_number'."
    )


def load_requests():
    """
    Загружает основную таблицу заявок.
    Ожидается файл:
    - data/local/requests.csv
    или
    - data/local/requests.xlsx
    """

    df = _read_table("requests")

    if df.empty:
        return pd.DataFrame()

    df = _ensure_key_column(df, "requests.csv/xlsx")

    # Убираем пустые ключи
    df = df[df[KEY_COLUMN] != ""]

    # Считаем, что в основной таблице одна строка на заявку.
    # Если есть дубли, оставляем первую.
    df = df.drop_duplicates(subset=[KEY_COLUMN], keep="first")

    # Сортировка по номеру заявки как тексту
    df = df.sort_values(
        KEY_COLUMN,
        key=lambda series: series.str.lower()
    ).reset_index(drop=True)

    return df


def load_request_details():
    """
    Загружает дополнительную таблицу по заявкам.
    Ожидается файл:
    - data/local/request_details.csv
    или
    - data/local/request_details.xlsx
    """

    df = _read_table("request_details")

    if df.empty:
        return pd.DataFrame()

    df = _ensure_key_column(df, "request_details.csv/xlsx")

    # Убираем пустые ключи
    df = df[df[KEY_COLUMN] != ""]

    # В дополнительной таблице может быть несколько строк на одну заявку
    return df