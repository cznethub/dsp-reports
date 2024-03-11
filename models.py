from datetime import datetime
from enum import Enum
from typing import List, Optional, Union

from beanie import Document, Link
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator


class StringEnum(str, Enum):
    pass


class RepositoryType(StringEnum):
    ZENODO = "zenodo"
    HYDROSHARE = "hydroshare"
    EARTHCHEM = "earthchem"
    EXTERNAL = "external"


class Submission(Document):
    title: str = None
    authors: List[str] = []
    repo_type: RepositoryType = None
    identifier: str = None
    submitted: datetime = datetime.utcnow()
    url: HttpUrl = None
    metadata_json: str = "{}"

    @validator('authors', pre=True, allow_reuse=True)
    def extract_author_names(cls, values):
        authors = []
        for author in values:
            if hasattr(author, 'name'):
                authors.append(author.name)
            else:
                authors.append(author)
        return authors


class User(Document):
    name: str
    email: Optional[EmailStr]
    orcid: str
    access_token: Optional[str]
    orcid_access_token: Optional[str]
    submissions: List[Link[Submission]] = []

    def submission(self, identifier: str) -> Submission:
        return next(filter(lambda submission: submission.identifier == identifier, self.submissions), None)

