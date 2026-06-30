from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseMutation(ABC):
    """Base class for all dataset mutations."""
    
    @property
    @abstractmethod
    def mutation_type(self) -> str:
        pass
        
    @abstractmethod
    def apply(self, record: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies a mutation to the record if the config dictates it.
        Returns a dictionary mapping field -> mutation applied, for tracking.
        If no mutation was applied, returns an empty dict.
        """
        pass
