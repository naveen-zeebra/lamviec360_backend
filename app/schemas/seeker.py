from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class SeekerProfileUpdate(BaseModel):
    personal: Optional[Dict[str, Any]] = None
    professional: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = None
    education: Optional[List[Dict[str, Any]]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    preferences: Optional[Dict[str, Any]] = None
    privacy: Optional[Dict[str, Any]] = None


class ResumeUploadRequest(BaseModel):
    file_name: str
    size: int
    data_url: Optional[str] = None


class SeekerProfileOut(BaseModel):
    user_id: str
    personal: Dict[str, Any]
    professional: Dict[str, Any]
    languages: List[str]
    education: List[Dict[str, Any]]
    experience: List[Dict[str, Any]]
    resume: Dict[str, Any]
    preferences: Dict[str, Any]
    completeness: int
