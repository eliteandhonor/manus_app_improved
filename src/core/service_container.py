
"""
Service Container for Dependency Injection.
Manages application dependencies and provides a centralized way to access services.
"""

from typing import Dict, Any, Type, Optional, TypeVar, cast

T = TypeVar('T')

class ServiceContainer:
    """
    Service container for dependency injection.
    Manages application dependencies and provides a centralized way to access services.
    """
    
    def __init__(self) -> None:
        """Initialize an empty service container."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._instances: Dict[str, Any] = {}
    
    def register(self, service_name: str, service: Any) -> None:
        """
        Register a service instance.
        
        Args:
            service_name: Name of the service
            service: Service instance
        """
        self._services[service_name] = service
    
    def register_factory(self, service_name: str, factory: callable) -> None:
        """
        Register a factory function that creates a service instance.
        The factory will be called only when the service is first requested.
        
        Args:
            service_name: Name of the service
            factory: Factory function that creates the service
        """
        self._factories[service_name] = factory
    
    def get(self, service_name: str) -> Any:
        """
        Get a service by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
        """
        # Return existing instance if available
        if service_name in self._services:
            return self._services[service_name]
        
        # Create instance from factory if available
        if service_name in self._factories:
            if service_name not in self._instances:
                self._instances[service_name] = self._factories[service_name]()
            return self._instances[service_name]
        
        raise KeyError(f"Service '{service_name}' not registered")
    
    def get_typed(self, service_name: str, service_type: Type[T]) -> T:
        """
        Get a service by name with type checking.
        
        Args:
            service_name: Name of the service
            service_type: Expected type of the service
            
        Returns:
            Service instance cast to the expected type
            
        Raises:
            KeyError: If service is not registered
            TypeError: If service is not of the expected type
        """
        service = self.get(service_name)
        if not isinstance(service, service_type):
            raise TypeError(f"Service '{service_name}' is not of type {service_type.__name__}")
        return cast(service_type, service)
    
    def has(self, service_name: str) -> bool:
        """
        Check if a service is registered.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if service is registered, False otherwise
        """
        return service_name in self._services or service_name in self._factories
