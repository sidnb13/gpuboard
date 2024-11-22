from .base import Backend, BackendType
from .lambda_labs import LambdaBackend


class BackendFactory:
    """Factory class to create different cloud backend instances."""

    @staticmethod
    def create_backend(backend_type: BackendType, **kwargs) -> Backend:
        """Create and return a backend instance based on the specified type."""
        backends = {
            BackendType.LAMBDA_LABS: lambda: LambdaBackend(
                api_key=kwargs.get("api_key")
            ),
            # Add other backends here as they're implemented
        }

        if backend_type not in backends:
            raise ValueError(f"Unsupported backend type: {backend_type}")

        return backends[backend_type]()


__all__ = ["Backend", "LambdaBackend", "BackendFactory"]
