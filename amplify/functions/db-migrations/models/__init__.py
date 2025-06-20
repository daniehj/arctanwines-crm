# Models package for Arctan Wines CRM
from .base import Base, BaseModel
from .wine_batch import WineBatch, WineBatchStatus

__all__ = [
    'Base', 
    'BaseModel',
    'WineBatch', 
    'WineBatchStatus'
] 