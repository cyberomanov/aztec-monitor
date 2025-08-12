from pydantic import BaseModel


class CsvAccount(BaseModel):
    id: int
    address: str
    ip: str
    port: int
    note: str = None
