from pydantic import BaseModel


class Block(BaseModel):
    number: int
    hash: str


class LatestBlockResult(BaseModel):
    latest: Block
    proven: Block
    finalized: Block


class LatestBlockResponse(BaseModel):
    jsonrpc: str
    id: int
    result: LatestBlockResult
