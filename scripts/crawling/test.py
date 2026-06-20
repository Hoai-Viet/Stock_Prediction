from vnstock import Finance
from dotenv import load_dotenv
import os

load_dotenv()

finance = Finance(symbol="DPD", source="KBS")

df = finance.balance_sheet(period="year")

metric_list = []
for metric in df["item"].unique():
    metric_list.append(metric)

print(metric_list)
