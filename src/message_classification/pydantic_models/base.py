"""
Base validation functionality for all Pydantic models.

Provides centralized validation that ensures every field has a description.
This validation happens automatically at module load time.
"""

from pydantic import BaseModel


class ValidatedBaseModel(BaseModel):
    """
    Base class for all Pydantic models with automatic field description validation.
    
    All subclasses are automatically validated at load time to ensure every field
    has a description. This prevents runtime errors and ensures consistent documentation.
    """
    
    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Validate the subclass at definition time (load time)"""
        super().__init_subclass__(**kwargs)
        cls._validate_field_descriptions()
    
    @classmethod
    def _validate_field_descriptions(cls):
        """Validate that all fields have descriptions - called automatically at load time"""
        for field_name, field_info in cls.model_fields.items():
            if not field_info.description:
                raise ValueError(
                    f"Field '{field_name}' in {cls.__name__} must have a description. "
                    f"Add description=... to the Field() definition."
                )
        
        # Log successful validation (optional)
        print(f"✅ {cls.__name__} validated: all fields have descriptions")


