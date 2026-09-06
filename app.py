import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Дашборд проектов",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_demo_data():
    """
    Пока используем демонстрационные данные.
    На следующем шаге заменим их на чтение ваших файлов.
    """

    projects = pd.DataFrame(
        [
            {
                "project_id": "P001",
                "name": "Объект №1",
                "customer": "Заказчик А",
                "status": "В работе",
            },
            {
                "project_id": "P002",
                "name": "Объект №2",
                "customer": "Заказчик Б",
                "status": "Ожидание",
            },
            {
                "project_id": "P003",
                "name": "Объект №3",
                "customer": "Заказчик В",
                "status": "Завершен",
            },
        ],
        dtype="string",
    )

    requests = pd.DataFrame(
        [
            {
                "request_id": "REQ-0001",
                "project_id": "P001",
                "title": "Заявка на монтаж",
                "date": "2026-08-01",
                "status": "В работе",
            },
            {
                "request_id": "REQ-0002",
                "project_id": "P001",
                "title": "Заявка на поставку",
                "date": "2026-08-12",
                "status": "Открыта",
            },
            {
                "request_id": "REQ-0003",
                "project_id": "P002",
                "title": "Заявка на проектирование",
                "date": "2026-08-15",
                "status": "Открыта",
            },
            {
                "request_id": "REQ-0004",
                "project_id": "P003",
                "title": "Заявка на сдачу",
                "date": "2026-08-20",
                "status": "Закрыта",
            },
        ],
        dtype="string",
    )

    requests["date"] = pd.to_datetime(requests["date"], errors="coerce")

    return projects, requests


projects, requests = load_demo_data()

st.title("Дашборд проектов")
st.caption("Это демонстрационные данные. Дальше подключим ваши таблицы.")

project_labels = {
    row["project_id"]: f"{row['project_id']} — {row['name']}"
    for _, row in projects.iterrows()
}

selected_project_id = st.sidebar.selectbox(
    label="Выберите проект",
    options=list(project_labels.keys()),
    format_func=lambda project_id: project_labels[project_id],
)

project_row = projects[projects["project_id"] == selected_project_id].iloc[0]

project_requests = requests[requests["project_id"] == selected_project_id].copy()

st.subheader("Карточка проекта")

c1, c2, c3, c4 = st.columns(4)

c1.metric("ID проекта", project_row["project_id"])
c2.metric("Название", project_row["name"])
c3.metric("Заказчик", project_row["customer"])
c4.metric("Статус", project_row["status"])

st.divider()

st.subheader("Заявки по проекту")

m1, m2 = st.columns([1, 3])

m1.metric("Количество заявок", len(project_requests))

if not project_requests.empty:
    last_date = project_requests["date"].max()
    if pd.notna(last_date):
        m2.metric("Последняя заявка", last_date.date())
    else:
        m2.metric("Последняя заявка", "-")
else:
    m2.metric("Последняя заявка", "-")

st.dataframe(
    project_requests.drop(columns=["project_id"]),
    use_container_width=True,
)