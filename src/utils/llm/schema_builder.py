from typing import Optional, Type, get_origin, get_args
from pydantic import BaseModel


class SchemaBuilder:
    def generate_schema_instructions(self, model_class: Type[BaseModel]) -> str:
        schema_parts = []
        
        for field_name, field_info in model_class.model_fields.items():
            field_type = self._get_field_type_name(field_info.annotation)
            description = field_info.description
            
            if not description:
                raise ValueError(
                    f"Field '{field_name}' in {model_class.__name__} must have a description. "
                    f"Add description=... to the Field() definition."
                )
            
            schema_parts.append(f"- {field_name} ({field_type}): {description}")
        
        return "\n".join(schema_parts)
    
    def _get_field_type_name(self, annotation) -> str:
        if get_origin(annotation) is type(None) or (get_origin(annotation) is type(Optional) and len(get_args(annotation)) == 2):
            args = get_args(annotation)
            if len(args) == 2 and type(None) in args:
                inner_type = args[0] if args[1] is type(None) else args[1]
                return f"{self._get_field_type_name(inner_type)} or null"
        
        if get_origin(annotation) is type(Optional):
            args = get_args(annotation)
            if len(args) == 2 and type(None) in args:
                inner_type = args[0] if args[1] is type(None) else args[1]
                return f"{self._get_field_type_name(inner_type)} or null"
        
        if annotation == bool:
            return "boolean"
        elif annotation == str:
            return "string"
        elif annotation == int:
            return "integer"
        elif annotation == float:
            return "number"
        elif hasattr(annotation, '__name__'):
            return annotation.__name__
        else:
            return str(annotation)
    
