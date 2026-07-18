from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SentenceLevelComment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence: str = Field(min_length=1)
    comment: str = Field(min_length=1)
    category: Literal["CONTENT", "LANGUAGE", "ORGANISATION", "MECHANICS", "OTHER"]


class RecommendedExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    exercise_type: str = Field(min_length=1)
    focus_area: str = Field(min_length=1)
    prompt: str = Field(min_length=1)


class AIMarkingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_score: int = Field(ge=0)
    language_score: int = Field(ge=0)
    organisation_score: int = Field(ge=0)
    total_score: int = Field(ge=0)
    confidence_level: Literal["LOW", "MEDIUM", "HIGH"]
    content_feedback: str = Field(min_length=1)
    language_feedback: str = Field(min_length=1)
    organisation_feedback: str = Field(min_length=1)
    strengths: list[str] = Field(min_length=1)
    weaknesses: list[str] = Field(min_length=1)
    sentence_level_comments: list[SentenceLevelComment]
    recommended_exercises: list[RecommendedExercise]
    warning_flags: list[str]
    model_metadata: dict[str, Any]


def validate_ai_marking_output(data: Any) -> AIMarkingOutput:
    return AIMarkingOutput.model_validate(data)


def ai_marking_json_schema() -> dict[str, Any]:
    return AIMarkingOutput.model_json_schema()
