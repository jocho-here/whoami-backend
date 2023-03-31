from typing import List

from pydantic import BaseModel, Field


class UpdateSingleLinkedProfileModel(BaseModel):
    source: str = Field(..., example="whoami")
    profile_link: str = Field(..., example="https://whoami.com/jocho")
    link_label: str = Field(..., example="My unique whoami profile")


class UpdateLinkedProfilesModel(BaseModel):
    linked_profiles: List[UpdateSingleLinkedProfileModel] = Field(...)
