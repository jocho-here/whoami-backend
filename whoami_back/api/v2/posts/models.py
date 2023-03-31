from typing import Optional

from pydantic import BaseModel, Field


class PostModel(BaseModel):
    # Required to be filled always
    id: str = Field(..., example="some uuid")
    x: int = Field(..., example=3)
    y: int = Field(..., example=3)
    height: int = Field(..., example=3)
    width: int = Field(..., example=3)
    scale: int = Field(..., example=1.0)

    # Other optional fields, at least one of them should be filled
    source: Optional[str] = Field(example="some source")
    content_uri: Optional[str] = Field(example="some uri")
    thumbnail_image_uri: Optional[str] = Field(example="some uri")
    title: Optional[str] = Field(example="some title")
    description: Optional[str] = Field(example="some description")
    b64_favicon: Optional[str] = Field(example="some favicon in base64 string")


class PostResponse(BaseModel):
    post: PostModel
