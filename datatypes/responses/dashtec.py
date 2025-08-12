from pydantic import BaseModel


class DashtecResponse(BaseModel):
    status: str
    balance: int = None
    unclaimedRewards: int = None
    attestationSuccess: str = None
    totalAttestationsSucceeded: int = None
    totalAttestationsMissed: int = None
    totalBlocksProposed: int = None
    totalBlocksMined: int = None
    totalBlocksMissed: int = None
