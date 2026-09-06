from pathlib import Path

import pandas as pd
import streamlit as st

from mapping_loader import load_mapped_table


KEY_COLUMN = "request_number"


st.set_page_config(
    page_title="Дашборд заявок",
    page_icon="📊",
    layout="wide",
)


def format_value(value):
    """
    Форматирует значение для показа.
    """

    if value is None:
        return ""

    if isinstance(value, pd.Timestamp):
        return value.strftime("%d.%m.%Y")

    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def show_record(record: pd.Series, display_map: dict):
    """
    Показывает одну запись в виде таблицы:
    Поле | Значение
    """

    rows = []

    for field_name, value in record.items():
        rows.append(
            {
                "Поле": display_map.get(field_name, field_name),
                "Значение": format_value(value),
            }
        )

    if not rows:
        st.info("Нет полей для отображения.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)


st.title("Дашборд заявок")
st.caption("Данные читаются из исходного файла по маппингу.")

if st.sidebar.button("Перечитать данные"):
    st.rerun()

try:
    result = load_mapped_table("requests")
except Exception as error:
    st.error(f"Ошибка загрузки данных: {error}")
    st.stop()


file_name = Path(result.source_file).name

st.sidebar.caption(f"Файл: {file_name}")
st.sidebar.caption(f"Лист: {result.sheet_name}")
st.sidebar.caption(f"Загружено строк: {len(result.df)}")


if result.warnings:
    with st.expander(f"Предупреждения: {len(result.warnings)}"):
        for warning in result.warnings:
            st.write(warning)


if result.df.empty:
    st.info(
        "Данные не найдены. "
        "Проверьте файл в папке data/local и настройки в config/mappings.yaml."
    )
    st.stop()


if KEY_COLUMN not in result.df.columns:
    st.error(
        f"В загруженных данных нет ключевого столбца '{KEY_COLUMN}'. "
        f"Проверьте параметр key_column в config/mappings.yaml."
    )
    st.stop()


request_numbers = result.df[KEY_COLUMN].astype(str).tolist()

selected_request = st.sidebar.selectbox(
    label="№ заявки",
    options=request_numbers,
)


selected_row = result.df[
    result.df[KEY_COLUMN] == selected_request
].iloc[0]


st.metric("Выбранная заявка", selected_request)

st.divider()

st.subheader("Данные по заявке")

record = selected_row.drop(labels=[KEY_COLUMN], errors="ignore")
show_record(record, result.display_map)


with st.expander("Служебная информация"):
    st.write(result.info)

    st.write("Загруженные поля:")

    columns_info = pd.DataFrame(
        [
            {
                "target": target,
                "display": result.display_map.get(target, target),
            }
            for target in result.ordered_columns
        ]
    )

    st.dataframe(columns_info, use_container_width=True)