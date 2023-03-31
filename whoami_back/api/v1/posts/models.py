from enum import Enum
from typing import Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, root_validator


class SourceSocialMedia(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    SPOTIFY = "spotify"
    MEDIUM = "medium"
    YOUTUBE = "youtube"
    WHOAMI = "whoami"
    UNKNOWN = "unknown"


class CreatePostModel(BaseModel):
    source: SourceSocialMedia = Field(..., example="whoami")
    content_uri: str = Field(..., example="https://whoami.com/content")
    x: int = Field(..., example=4)
    y: int = Field(..., example=4)
    width: int = Field(..., example=4)
    height: int = Field(..., example=4)
    scale: float = Field(..., example=4.0)

    # Optional
    thumbnail_image_uri: Optional[str] = Field(example="https://whoami.com/content")
    title: Optional[str] = Field(example="my wonderful post")
    description: Optional[str] = Field(example="some user written description")
    meta_title: Optional[str] = Field(example="this is the original title")
    meta_description: Optional[str] = Field(
        example="this is the original description"
    )


class UpdatePostModel(BaseModel):
    source: Optional[SourceSocialMedia] = Field(example="whoami")
    content_uri: Optional[str] = Field(example="https://whoami.com/content")
    x: Optional[int] = Field(example=4)
    y: Optional[int] = Field(example=4)
    width: Optional[int] = Field(example=4)
    height: Optional[int] = Field(example=4)
    scale: Optional[float] = Field(example=4.0)

    thumbnail_image_uri: Optional[str] = Field(example="https://whoami.com/content")
    title: Optional[str] = Field(example="my wonderful post")
    description: Optional[str] = Field(example="my wonderful post")
    meta_title: Optional[str] = Field(example="this is the original title")
    meta_description: Optional[str] = Field(
        example="this is the original description"
    )

    @root_validator(pre=True)
    def check_source_with_content_uri(cls, values):
        if ("content_uri" in values) != ("source" in values):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source and content_uri should either be both present or missing",
            )

        return values
