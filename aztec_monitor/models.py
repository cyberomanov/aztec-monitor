"""Pydantic models used by the Aztec monitor."""

from pydantic import BaseModel


class CsvAccount(BaseModel):
    """Representation of a validator account loaded from CSV."""

    id: int
    address: str
    ip: str
    port: int
    note: str | None = None


class Balance(BaseModel):
    """Numeric balance available both as int and float."""

    int: int
    float: float


class DashtecResponse(BaseModel):
    """Subset of data returned by the Dashtec API."""

    status: str
    balance: int | None = None
    unclaimedRewards: int | None = None
    attestationSuccess: str | None = None
    totalAttestationsSucceeded: int | None = None
    totalAttestationsMissed: int | None = None
    totalBlocksProposed: int | None = None
    totalBlocksMined: int | None = None
    totalBlocksMissed: int | None = None


class Block(BaseModel):
    """Block information returned by the node."""

    number: int
    hash: str


class LatestBlockResult(BaseModel):
    """Latest, proven and finalised block numbers."""

    latest: Block
    proven: Block
    finalized: Block


class LatestBlockResponse(BaseModel):
    """Response model for ``node_getL2Tips`` RPC call."""

    jsonrpc: str
    id: int
    result: LatestBlockResult


class TelegramResponse(BaseModel):
    """Response returned by the Telegram API."""

    ok: bool
    error_code: int | None = None
    description: str | None = None
