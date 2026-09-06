import pandas as pd
import streamlit as st

from data_loader import (
    load_requests,
    load_request_details,
    KEY_COLUMN,
)


st.set_page_config(
    page_title="Дашборд заявок",
    page_icon="📊",
    layout="wide",
)


def show_record(record: pd.Series):
    """
    Показывает одну запись в виде таблицы:
    Поле | Значение
    """

    df = pd.DataFrame(
        {
            "Поле": record.index,
            "Значение": record.values,
        }
    )

    st.dataframe(df, use_container_width=True)


st.title("Дашборд заявок")
st.caption("Выберите номер заявки слева.")

try:
    requests = load_requests()
    details = load_request_details()
except Exception as error:
    st.error(f"Ошибка загрузки данных: {error}")
    st.stop()


if requests.empty:
    st.info(
        "Нет данных для отображения. "
        "Создайте демо-данные или положите файлы в папку data/local."
    )

    st.subheader("Как создать демо-данные")
    st.code("python tools/create_sample_local_data.py", language="bash")

    st.subheader("Какие файлы можно положить в data/local")
    st.write(
        """
        - requests.csv или requests.xlsx — основная таблица заявок  
        - request_details.csv или request_details.xlsx — дополнительные данные  

        В таблицах должен быть столбец с номером заявки, например:
        - № заявки
        - Номер заявки
        - request_number
        """
    )

    st.stop()


# Список номеров заявок для выбора
request_numbers = requests[KEY_COLUMN].tolist()

selected_request = st.sidebar.selectbox(
    label="№ заявки",
    options=request_numbers,
)

st.sidebar.caption("Данные читаются из папки data/local")

# Получаем основную строку по выбранной заявке
request_row = requests[requests[KEY_COLUMN] == selected_request].iloc[0]

# Получаем дополнительные строки по выбранной заявке
if not details.empty and KEY_COLUMN in details.columns:
    detail_rows = details[details[KEY_COLUMN] == selected_request].copy()
else:
    detail_rows = pd.DataFrame()


st.metric("Выбранная заявка", selected_request)

st.divider()

st.subheader("Основная информация по заявке")

# Показываем все поля основной таблицы, кроме служебного ключа
main_record = request_row.drop(labels=[KEY_COLUMN], errors="ignore")
show_record(main_record)

st.divider()

st.subheader("Дополнительные данные по заявке")

if detail_rows.empty:
    st.info("Нет дополнительных данных для выбранной заявки.")
else:
    # Убираем служебный столбец с ключом, чтобы не дублировать его
    detail_table = detail_rows.drop(columns=[KEY_COLUMN], errors="ignore")
    st.dataframe(detail_table, use_container_width=True)