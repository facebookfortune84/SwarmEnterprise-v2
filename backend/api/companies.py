"""
Companies API endpoints for managing generated companies
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from backend.auth.middleware import get_current_active_user
from backend.services.company_generator import (
    CompanyGenerator,
    CompanyRequest,
    TechStack,
    GenerationStatus
)
from backend.storage.file_manager import FileManager


router = APIRouter(prefix="/api/companies", tags=["companies"])
generator = CompanyGenerator()
file_manager = FileManager()


class GenerateCompanyRequest(BaseModel):
    """Request to generate a new company"""
    name: str
    description: str
    tech_stack: TechStack
    features: List[str] = []


class CompanyResponse(BaseModel):
    """Company response schema"""
    id: str
    name: str
    slug: str
    description: str
    tech_stack: str
    status: str
    user_id: str
    created_at: str
    generation_started_at: Optional[str] = None
    generation_completed_at: Optional[str] = None
    download_count: int = 0
    storage_path: Optional[str] = None


class CompanyStatusResponse(BaseModel):
    """Company generation status response"""
    company_id: str
    status: str
    progress_percent: Optional[int] = None
    message: Optional[str] = None
    estimated_time_remaining: Optional[int] = None


@router.post("/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_company(
    request: GenerateCompanyRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Generate a new company application
    
    Args:
        request: Company generation request
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        
    Returns:
        Generation info with company ID and status
    """
    # Create company request
    company_request = CompanyRequest(
        name=request.name,
        description=request.description,
        tech_stack=request.tech_stack,
        features=request.features,
        user_id=current_user["id"]
    )
    
    # Start generation
    result = await generator.generate_company(company_request)
    
    # TODO: Add background task for actual generation
    # background_tasks.add_task(generator._execute_generation, result["company_id"], company_request)
    
    return result


@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """
    List all companies for current user
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Optional status filter
        current_user: Current authenticated user
        
    Returns:
        List of companies
    """
    # TODO: Query database
    # companies = db.query(Company).filter(Company.user_id == current_user["id"])
    # if status_filter:
    #     companies = companies.filter(Company.status == status_filter)
    # companies = companies.offset(skip).limit(limit).all()
    
    return []


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get company by ID
    
    Args:
        company_id: Company ID
        current_user: Current authenticated user
        
    Returns:
        Company details
        
    Raises:
        HTTPException: If company not found or access denied
    """
    # Get company from generator (in-memory for now)
    company = generator.get_generation_status(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check ownership
    if company["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return company


@router.get("/{company_id}/status", response_model=CompanyStatusResponse)
async def get_company_status(
    company_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get company generation status
    
    Args:
        company_id: Company ID
        current_user: Current authenticated user
        
    Returns:
        Generation status
    """
    company = generator.get_generation_status(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check ownership
    if company["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Calculate progress
    progress = 0
    if company["status"] == GenerationStatus.COMPLETED.value:
        progress = 100
    elif company["status"] == GenerationStatus.FAILED.value:
        progress = 0
    elif company["status"] == GenerationStatus.PACKAGING.value:
        progress = 90
    elif company["status"] == GenerationStatus.EXECUTING_TICKETS.value:
        progress = 60
    elif company["status"] == GenerationStatus.GENERATING_TICKETS.value:
        progress = 30
    elif company["status"] == GenerationStatus.INITIALIZING.value:
        progress = 10
    
    return CompanyStatusResponse(
        company_id=company_id,
        status=company["status"],
        progress_percent=progress,
        message=company.get("error") or f"Status: {company['status']}"
    )


@router.get("/{company_id}/download")
async def download_company(
    company_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get download URL for company archive
    
    Args:
        company_id: Company ID
        current_user: Current authenticated user
        
    Returns:
        Presigned download URL
    """
    company = generator.get_generation_status(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check ownership
    if company["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if generation is complete
    if company["status"] != GenerationStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company generation not complete"
        )
    
    # Check if file exists in storage
    if not file_manager.company_exists(company_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company archive not found in storage"
        )
    
    # Generate presigned URL (valid for 1 hour)
    download_url = file_manager.get_company_download_url(company_id, expiration=3600)
    
    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )
    
    # TODO: Increment download count in database
    # company.download_count += 1
    # db.commit()
    
    return {
        "download_url": download_url,
        "expires_in": 3600,
        "company_id": company_id,
        "company_name": company["name"]
    }


@router.delete("/{company_id}")
async def delete_company(
    company_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Delete a company
    
    Args:
        company_id: Company ID
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    company = generator.get_generation_status(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check ownership
    if company["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Delete from storage
    if file_manager.company_exists(company_id):
        file_manager.delete_company(company_id)
    
    # TODO: Delete from database
    # db.query(Company).filter(Company.id == company_id).delete()
    # db.commit()
    
    return {"message": "Company deleted successfully"}


@router.post("/{company_id}/regenerate", response_model=dict)
async def regenerate_company(
    company_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Regenerate a company
    
    Args:
        company_id: Company ID
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        
    Returns:
        New generation info
    """
    company = generator.get_generation_status(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check ownership
    if company["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Create new generation request with same parameters
    company_request = CompanyRequest(
        name=company["name"],
        description=company["description"],
        tech_stack=TechStack(company["tech_stack"]),
        features=company["metadata"].get("features", []),
        user_id=current_user["id"]
    )
    
    # Start new generation
    result = await generator.generate_company(company_request)
    
    return result


@router.get("/{company_id}/metadata")
async def get_company_metadata(
    company_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get company metadata
    
    Args:
        company_id: Company ID
        current_user: Current authenticated user
        
    Returns:
        Company metadata
    """
    company = generator.get_generation_status(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check ownership
    if company["user_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return {
        "company_id": company_id,
        "metadata": company.get("metadata", {}),
        "storage_metadata": file_manager.get_company_metadata(company_id)
    }

# Made with Bob
