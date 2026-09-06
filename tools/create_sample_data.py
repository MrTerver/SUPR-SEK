from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "local"
DATA_DIR.mkdir(parents=True, exist_ok=True)


requests_data = pd.DataFrame(
    [
        {
            "№ заявки": "ЗВ-2026-001",
            "Объект": "Объект №1",
            "Заказчик": "Заказчик А",
            "Статус": "В работе",
            "Дата заявки": "2026-08-01",
        },
        {
            "№ заявки": "ЗВ-2026-002",
            "Объект": "Объект №2",
            "Заказчик": "Заказчик Б",
            "Статус": "Открыта",
            "Дата заявки": "2026-08-10",
        },
        {
            "№ заявки": "ЗВ-2026-003",
            "Объект": "Объект №3",
            "Заказчик": "Заказчик В",
            "Статус": "Закрыта",
            "Дата заявки": "2026-08-20",
        },
    ],
    dtype="string",
)


details_data = pd.DataFrame(
    [
        {
            "№ заявки": "ЗВ-2026-001",
            "Ответственный": "Иванов И.И.",
            "Договор": "Д-001",
            "Сумма": "120000",
            "Примечание": "Монтаж до 15.09.2026",
        },
        {
            "№ заявки": "ЗВ-2026-001",
            "Ответственный": "Петров П.П.",
            "Договор": "Д-001",
            "Сумма": "45000",
            "Примечание": "Поставка материала",
        },
        {
            "№ заявки": "ЗВ-2026-002",
            "Ответственный": "Сидоров С.С.",
            "Договор": "Д-002",
            "Сумма": "",
            "Примечание": "Ожидаем проектную документацию",
        },
    ],
    dtype="string",
)


requests_path = DATA_DIR / "requests.csv"
details_path = DATA_DIR / "request_details.csv"


def save_file(df: pd.DataFrame, path: Path):
    if path.exists():
        print(f"Файл уже существует, пропускаю: {path}")
    else:
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"Создан файл: {path}")


save_file(requests_data, requests_path)
save_file(details_data, details_path)

print()
print("Демо-данные находятся в папке:")
print(DATA_DIR)