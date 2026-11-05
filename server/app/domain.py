from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .scenes import Scene


class Step(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    detail: str = Field(min_length=1, max_length=1200)


class CodeStep(BaseModel):
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    explanation: str = Field(min_length=1, max_length=1500)
    variables: str = Field(default='', max_length=1500)


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text", "callout", "diagram", "quiz", "code", "scene", "source"]
    title: str = Field(default="", max_length=150)
    body: str = Field(default="", max_length=14000)
    source_ids: list[str] = Field(default_factory=list, max_length=12)
    steps: list[Step] = Field(default_factory=list, max_length=8)
    options: list[str] = Field(default_factory=list, max_length=6)
    answer: int | None = None
    explanation: str = Field(default="", max_length=2000)
    scene: Scene | None = None
    code_trace: list[CodeStep] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_shape(self):
        if self.code_trace and (self.type!='code' or any(s.line_start>s.line_end or s.line_end>len(self.body.splitlines()) for s in self.code_trace)):
            raise ValueError('代码推演必须引用实际存在的行')
        if self.type == 'scene' and self.scene is None:
            raise ValueError('场景需要提供具体对象、关系和变化')
        if self.type == "diagram" and len(self.steps) < 2:
            raise ValueError("图解至少需要两个步骤")
        if self.type == "quiz" and (len(self.options) < 2 or self.answer is None or not 0 <= self.answer < len(self.options)):
            raise ValueError("练习需要选项和合法答案")
        return self


class Lesson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=800)
    blocks: list[Block] = Field(min_length=1, max_length=10)


class TeachingChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=300, description="本轮要帮助用户理解的具体问题")
    approach: str = Field(min_length=1, max_length=300, description="自由选择教学方式，不受 action 枚举限制")
    success_signal: str = Field(max_length=300, description="什么可观察的表现能够支持理解，不能声称已掌握")


class RouteChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    unit_id: str
    category: Literal['learn', 'guide', 'skip']
    reason: str = Field(min_length=1, max_length=300)


class CurriculumReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choices: list[RouteChoice] = Field(min_length=1, max_length=20)


class TutorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["answer", "clarify", "reexplain", "worked_example", "step_diagram", "micro_exercise"]
    reason: str = Field(max_length=300)
    teaching: TeachingChoice
    blocks: list[Block] = Field(min_length=1, max_length=6)


class TurnRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=100)
    unit_id: str
    message: str = Field(min_length=1, max_length=4000)
    selected_text: str = Field(default="", max_length=3000)
    intent: Literal["ask", "confused", "example", "diagram", "practice"] = "ask"


class ProgressRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=100)
    unit_id: str
    expected_version: int = Field(ge=0)
    block_index: int = Field(default=0, ge=0, le=100000)


class RegenerateRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=100)
    expected_revision: int = Field(ge=0)
    depth: Literal['quick','full'] = 'full'


class EventRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=100)
    unit_id: str
    kind: Literal["understood", "confused", "practice", "skip", "correction", "note"]
    text: str = Field(default="", max_length=3000)
    target_id: str | None = None
    block_index: int | None = Field(default=None, ge=0, le=100000)
    choice: int | None = None
    used_hint: bool = False
    lesson_revision: int = Field(default=0, ge=0)


class AppError(Exception):
    def __init__(self, message: str, code: str = "INVALID_REQUEST", status: int = 400):
        self.message, self.code, self.status = message, code, status
        super().__init__(message)
