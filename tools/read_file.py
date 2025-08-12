import csv
from typing import List

from datatypes.csv_account import CsvAccount


def read_file(path: str):
    result = []
    with open(path) as file:
        for line in file:
            line = line.rstrip("\n")
            if line and not line.startswith("# "):
                result.append(line)
    return result


def read_csv(csv_path: str) -> List[CsvAccount]:
    accounts = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            account = CsvAccount(
                id=int(row['id']),
                address=row['address'],
                ip=row['ip'],
                port=row['port'],
                note=row['note'],
            )
            accounts.append(account)
    return accounts
