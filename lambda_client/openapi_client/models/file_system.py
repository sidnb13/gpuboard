# coding: utf-8

"""
    Lambda Cloud API

    API for interacting with the Lambda GPU Cloud

    The version of the OpenAPI document: 1.5.3
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


from __future__ import annotations
import pprint
import re  # noqa: F401
import json

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from typing import Any, ClassVar, Dict, List, Optional
from openapi_client.models.region import Region
from openapi_client.models.user import User
from typing import Optional, Set
from typing_extensions import Self

class FileSystem(BaseModel):
    """
    Information about a shared file system
    """ # noqa: E501
    id: StrictStr = Field(description="Unique identifier (ID) of a file system")
    name: StrictStr = Field(description="Name of a file system")
    created: StrictStr = Field(description="A date and time, formatted as an ISO 8601 time stamp")
    created_by: User
    mount_point: StrictStr = Field(description="Absolute path indicating where on instances the file system will be mounted")
    region: Region
    is_in_use: StrictBool = Field(description="Whether the file system is currently in use by an instance. File systems that are in use cannot be deleted.")
    bytes_used: Optional[StrictInt] = Field(default=None, description="Approximate amount of storage used by the file system, in bytes. This value is an estimate that is updated every several hours.")
    __properties: ClassVar[List[str]] = ["id", "name", "created", "created_by", "mount_point", "region", "is_in_use", "bytes_used"]

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Optional[Self]:
        """Create an instance of FileSystem from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: Set[str] = set([
        ])

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of created_by
        if self.created_by:
            _dict['created_by'] = self.created_by.to_dict()
        # override the default output from pydantic by calling `to_dict()` of region
        if self.region:
            _dict['region'] = self.region.to_dict()
        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of FileSystem from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "id": obj.get("id"),
            "name": obj.get("name"),
            "created": obj.get("created"),
            "created_by": User.from_dict(obj["created_by"]) if obj.get("created_by") is not None else None,
            "mount_point": obj.get("mount_point"),
            "region": Region.from_dict(obj["region"]) if obj.get("region") is not None else None,
            "is_in_use": obj.get("is_in_use"),
            "bytes_used": obj.get("bytes_used")
        })
        return _obj


