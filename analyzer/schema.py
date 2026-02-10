from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class FieldType(str, Enum):
    TEXT = "text"
    EMAIL = "email"
    PASSWORD = "password"
    NUMBER = "number"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    FILE = "file"
    SELECT = "select"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    HIDDEN = "hidden"
    URL = "url"
    PHONE = "phone"
    STRING = "string"
    FOREIGN_KEY = "foreign_key"
    JSON = "json"
    UNKNOWN = "unknown"


class FormField(BaseModel):
    """A single field within a form."""

    name: str
    field_type: FieldType = FieldType.TEXT
    required: bool = False
    label: str = ""
    placeholder: str = ""
    default_value: str = ""
    test_id: str = ""
    selector: str = ""
    validation_rules: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)


class InteractiveElement(BaseModel):
    """A clickable or interactive UI element (button, link, etc.)."""

    element_type: str = "button"
    text: str = ""
    test_id: str = ""
    selector: str = ""
    action: str = ""
    href: str = ""


class FormDefinition(BaseModel):
    """A form discovered in the source code."""

    name: str
    action_url: str = ""
    method: HttpMethod = HttpMethod.POST
    fields: list[FormField] = Field(default_factory=list)
    submit_button: InteractiveElement | None = None
    source_file: str = ""
    test_id: str = ""
    selector: str = ""


class PageDefinition(BaseModel):
    """A page/route discovered in the source code."""

    name: str
    path: str
    title: str = ""
    component: str = ""
    source_file: str = ""
    requires_auth: bool = False
    forms: list[FormDefinition] = Field(default_factory=list)
    interactive_elements: list[InteractiveElement] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    test_ids: list[str] = Field(default_factory=list)


class ModelField(BaseModel):
    """A field within a data model."""

    name: str
    field_type: FieldType = FieldType.STRING
    required: bool = True
    unique: bool = False
    primary_key: bool = False
    max_length: int | None = None
    default: str | None = None
    choices: list[str] = Field(default_factory=list)
    related_model: str = ""


class ModelDefinition(BaseModel):
    """A data model (ORM model, Pydantic schema, etc.) discovered in the source code."""

    name: str
    fields: list[ModelField] = Field(default_factory=list)
    source_file: str = ""
    table_name: str = ""
    base_class: str = ""
    relationships: list[str] = Field(default_factory=list)


class EndpointDefinition(BaseModel):
    """An API endpoint discovered in the source code."""

    path: str
    method: HttpMethod = HttpMethod.GET
    name: str = ""
    view_name: str = ""
    source_file: str = ""
    request_model: str = ""
    response_model: str = ""
    requires_auth: bool = False
    path_params: list[str] = Field(default_factory=list)
    query_params: list[str] = Field(default_factory=list)
    description: str = ""


class FrontendBackendMapping(BaseModel):
    """A discovered link between a frontend page/form and a backend endpoint."""

    page_name: str = ""
    form_name: str = ""
    endpoint_path: str = ""
    endpoint_method: HttpMethod = HttpMethod.GET
    confidence: float = 0.0
    strategy: str = ""


class TechStackInfo(BaseModel):
    """Detected technology stack information."""

    framework: str
    confidence: float
    version: str = ""
    language: str = ""
    detected_files: list[str] = Field(default_factory=list)


class DiscoveryResult(BaseModel):
    """The complete result of source code analysis."""

    source_dir: str
    tech_stack: list[TechStackInfo] = Field(default_factory=list)
    pages: list[PageDefinition] = Field(default_factory=list)
    endpoints: list[EndpointDefinition] = Field(default_factory=list)
    models: list[ModelDefinition] = Field(default_factory=list)
    forms: list[FormDefinition] = Field(default_factory=list)
    mappings: list[FrontendBackendMapping] = Field(default_factory=list)

    def to_json_file(self, path: str | Path) -> None:
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(self.model_dump_json(indent=2))

    @classmethod
    def from_json_file(cls, path: str | Path) -> DiscoveryResult:
        filepath = Path(path)
        return cls.model_validate_json(filepath.read_text())
