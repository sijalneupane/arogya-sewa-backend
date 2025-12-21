from pydantic import BaseModel, ConfigDict, Field


class FileResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: str = Field(..., description="Unique identifier for the file")
    file_url: str = Field(..., description="Name of the file")
    meta_type: str = Field(..., description="MIME type of the file")
    file_type: str = Field(..., description="URL to access the file")
