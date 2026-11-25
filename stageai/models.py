from typing import Literal
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator
import math


class Dimensions(BaseModel):
    width: float = Field(default=5, ge=1, le=50)
    depth: float = Field(default=4, ge=1, le=50)
    height: float = Field(default=2.7, ge=1.8, le=10)
    source: Literal["estimated", "user-measured"] = "estimated"


class Reconstruction(BaseModel):
    mode: Literal["guided", "worldbuilder"] = "guided"
    room_type: Literal["living", "bedroom", "office", "other"] = "living"
    dimensions: Dimensions = Field(default_factory=Dimensions)
    quality: Literal["medium", "high"] = "medium"
    rotation: Literal[0, 90, 180, 270] = 0
    crop: list[float] = Field(default_factory=lambda: [0, 0, 1, 1], min_length=4, max_length=4)
    floor_corners: list[list[float]] = Field(default_factory=lambda: [[.25,.58],[.75,.58],[.98,.98],[.02,.98]], min_length=4, max_length=4)

    @field_validator("crop")
    @classmethod
    def valid_crop(cls, v):
        if not all(math.isfinite(x) and 0 <= x <= 1 for x in v) or v[2]-v[0] < .1 or v[3]-v[1] < .1:
            raise ValueError("Crop must be [left, top, right, bottom] in 0..1 with at least 10% width/height")
        return v

    @field_validator("floor_corners")
    @classmethod
    def valid_corners(cls, v):
        if any(len(p) != 2 or any(not math.isfinite(x) or not 0 <= x <= 1 for x in p) for p in v):
            raise ValueError("Four floor corners must be normalized image coordinates")
        cross = []
        for i in range(4):
            a,b,c = v[i],v[(i+1)%4],v[(i+2)%4]
            cross.append((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))
        area = abs(sum(v[i][0]*v[(i+1)%4][1]-v[(i+1)%4][0]*v[i][1] for i in range(4)))/2
        if not (all(c>1e-6 for c in cross) or all(c< -1e-6 for c in cross)) or area < .005:
            raise ValueError("Floor corners must form a non-intersecting convex quadrilateral in order")
        return v


class SceneObject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    name: str = Field(min_length=1, max_length=150)
    kind: Literal["bed","sofa","chair","table","desk","wardrobe","cabinet","shelf","lamp","rug","plant","decor","door","window","mesh"]
    group: Literal["furniture","decorative","structure"] = "furniture"
    position: list[float] = Field(min_length=3,max_length=3)
    rotation: float = Field(default=0, ge=-36000,le=36000)
    dimensions: list[float] = Field(min_length=3,max_length=3)
    color: str = Field(default="#a8b4ac", pattern=r"^#[0-9a-fA-F]{6}$")
    asset: str | None = None
    node: int | None = Field(default=None, ge=0)
    mesh_name: str | None = Field(default=None, max_length=150)
    visible: bool = True
    evidence: str = Field(default="procedural asset", max_length=300)

    @field_validator("position")
    @classmethod
    def finite_position(cls,v):
        if any(not math.isfinite(x) or abs(x)>1000 for x in v):
            raise ValueError("Position must be finite and within 1000 metres")
        return v

    @field_validator("dimensions")
    @classmethod
    def valid_size(cls,v):
        if any(not math.isfinite(x) or not .001<=x<=100 for x in v):
            raise ValueError("Object dimensions must be .001..100 metres")
        return v


class SceneState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    name: str = Field(default="Untitled room", min_length=1, max_length=150)
    room: Dimensions = Field(default_factory=Dimensions)
    room_type: Literal["living","bedroom","office","other"] = "living"
    shell: bool = True
    floor_texture: str | None = None
    wall_color: str = Field(default="#e1e5e2",pattern=r"^#[0-9a-fA-F]{6}$")
    objects: list[SceneObject] = Field(default_factory=list,max_length=1500)
    camera: dict = Field(default_factory=dict)
    settings: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list,max_length=200)
    provenance: str = "manual"

    @field_validator("camera", "settings")
    @classmethod
    def valid_metadata(cls, value):
        try:
            encoded=json.dumps(value,allow_nan=False)
        except (TypeError,ValueError) as exc:
            raise ValueError("Metadata must contain finite JSON values") from exc
        if len(encoded)>2*1024*1024:
            raise ValueError("Metadata exceeds 2 MB")
        return value

