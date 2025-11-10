from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from app.core.verifier import EmailVerifier
from app.models.results import VerificationResult
import asyncio

app = FastAPI(title="Email Verification Service", version="1.0.0")
verifier = EmailVerifier()


class EmailRequest(BaseModel):
    email: str


class BulkEmailRequest(BaseModel):
    emails: List[str]


class VerificationResponse(BaseModel):
    success: bool
    data: Optional[VerificationResult] = None
    error: Optional[str] = None


class BulkVerificationResponse(BaseModel):
    success: bool
    data: List[VerificationResult]
    total: int
    valid_count: int


@app.get("/")
async def root():
    return {"message": "Email Verification Service", "status": "running"}


@app.post("/verify", response_model=VerificationResponse)
async def verify_email(request: EmailRequest):
    try:
        result = await verifier.verify_single(request.email)
        return VerificationResponse(success=True, data=result)
    except Exception as e:
        return VerificationResponse(success=False, error=str(e))


@app.post("/verify-bulk", response_model=BulkVerificationResponse)
async def verify_bulk_emails(request: BulkEmailRequest):
    try:
        results = await verifier.verify_bulk(request.emails)
        valid_count = sum(1 for r in results if r.is_verified)

        return BulkVerificationResponse(
            success=True,
            data=results,
            total=len(results),
            valid_count=valid_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TEST ENDPOINTS
@app.get("/test/single")
async def test_single_verification():
    """Test endpoint for single verification"""
    result = await verifier.verify_single("bookf826@gmail.com")
    return {
        "email": result.email,
        "status": result.status,
        "quality_score": result.quality_score,
        "verified": result.is_verified,
        "details": result.details
    }


@app.get("/test/bulk")
async def test_bulk_verification():
    emails = [
        "ariful.inovace@gmail.com",
        "test@inovace@gmail.com",
        "qa@inovactech@gmail.com",
        "mahir@inovacetech.com",
        "fahim@inovacetech.com",
        "ikshimul.inovace@gmail.com",
        "snigdha.inovace@gmail.com",
        "annoy.inovace@gmail.com",
    ]

    results = await verifier.verify_bulk(emails)

    return {
        "results": [
            {
                "email": r.email,
                "status": r.status,
                "quality_score": r.quality_score,
                "verified": r.is_verified
            }
            for r in results
        ],
        "summary": {
            "total": len(results),
            "valid": sum(1 for r in results if r.is_verified)
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "email_verification"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)