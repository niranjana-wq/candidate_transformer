from typing import TypeVar, Generic

T = TypeVar('T')

class RegistryError(Exception):
    """Custom exception for registry operations."""
    pass

class Registry(Generic[T]):
    """
    A generic registry for registering and retrieving components like adapters, 
    normalizers, and strategies by a string key.
    Enforces the Open/Closed Principle by avoiding hardcoded if/else chains.
    """
    
    def __init__(self, registry_name: str):
        self.name = registry_name
        self._items: dict[str, T] = {}

    def register(self, key: str, item: T) -> None:
        """
        Register an item with a unique key.
        Raises RegistryError if the key is already registered.
        """
        if key in self._items:
            raise RegistryError(f"Cannot register '{key}' in {self.name} registry: Key already exists.")
        self._items[key] = item

    def get(self, key: str) -> T:
        """
        Retrieve an item by its key.
        Raises RegistryError if the key is not found.
        """
        if key not in self._items:
            raise RegistryError(f"Item '{key}' not found in {self.name} registry.")
        return self._items[key]
        
    def get_all(self) -> dict[str, T]:
        """
        Returns a copy of all registered items.
        """
        return self._items.copy()
