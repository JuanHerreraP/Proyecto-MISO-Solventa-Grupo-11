import hashlib

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="KYC Provider A Mock")


class VerificationRequest(BaseModel):
    documentType: str
    documentNumber: str
    fullName: str
    birthDate: str


class VerificationResponse(BaseModel):
    verificationId: str
    status: str
    score: int


@app.post("/kyc/verify", response_model=VerificationResponse)
def verify(payload: VerificationRequest) -> VerificationResponse:
    digest = int(
        hashlib.sha256(
            payload.documentNumber.encode()
        ).hexdigest(),
        16,
    )

    bucket = digest % 10

    if bucket < 7:
        status = "APPROVED"
        score = 15 + (digest % 20)

    elif bucket < 9:
        status = "PENDING"
        score = 45 + (digest % 20)

    else:
        status = "REJECTED"
        score = 80 + (digest % 20)

    return VerificationResponse(
        verificationId=(
            f"A-{payload.documentNumber}-{digest % 100000}"
        ),
        status=status,
        score=min(score, 100),
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": "A",
    }