from pydantic import BaseModel


class Balance(BaseModel):
    int: int
    float: float
