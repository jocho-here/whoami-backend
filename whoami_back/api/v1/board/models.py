from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BoardViewType(str, Enum):
    STACK = "stack"
    BOARD = "board"


class BoardBackgroundImageFittingMode(str, Enum):
    FILL = "fill"
    FIT = "fit"
    CENTER = "center"


class BoardBackgroundModel(BaseModel):
    background_image_s3_uri: Optional[str] = Field(example="some uri")
    background_image_fitting_mode: Optional[BoardBackgroundImageFittingMode] = Field(
        example="fill"
    )
    background_hex_color: Optional[str] = Field(..., example="some hex code")
