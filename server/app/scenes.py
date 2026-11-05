"""Bounded, declarative scenes; model output never executes as browser code."""
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Node(Strict):
    id: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=35)
    x: float = Field(ge=0, le=740)
    y: float = Field(ge=35, le=410)


class Group(Strict):
    label: str = Field(min_length=1, max_length=50)
    x: float = Field(ge=0, le=900)
    y: float = Field(ge=0, le=500)
    width: float = Field(ge=100, le=900)
    height: float = Field(ge=80, le=500)

    @model_validator(mode='after')
    def fits(self):
        if self.x+self.width>900 or self.y+self.height>500:
            raise ValueError('分组超出画布')
        return self


class Edge(Strict):
    id: str = Field(min_length=1, max_length=50)
    source: str
    target: str
    label: str = Field(default='', max_length=25)


class NodeState(Strict):
    node_id: str
    text: str = Field(max_length=45)
    x: float | None = Field(default=None, ge=0, le=740)
    y: float | None = Field(default=None, ge=35, le=410)


class Frame(Strict):
    caption: str = Field(min_length=1, max_length=600)
    active_nodes: list[str] = Field(default_factory=list, max_length=10)
    active_edges: list[str] = Field(default_factory=list, max_length=16)
    states: list[NodeState] = Field(default_factory=list, max_length=10)


class Scenario(Strict):
    label: str = Field(min_length=1, max_length=40)
    frames: list[Frame] = Field(min_length=2, max_length=10)


class Scene(Strict):
    goal: str = Field(min_length=1, max_length=300)
    nodes: list[Node] = Field(min_length=2, max_length=10)
    groups: list[Group] = Field(default_factory=list, max_length=4)
    edges: list[Edge] = Field(default_factory=list, max_length=16)
    scenarios: list[Scenario] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def references(self):
        nodes={n.id for n in self.nodes}; edges={e.id for e in self.edges}
        if len(nodes)!=len(self.nodes) or len(edges)!=len(self.edges):
            raise ValueError('场景 ID 不能重复')
        if any(e.source not in nodes or e.target not in nodes for e in self.edges):
            raise ValueError('连线必须连接已有对象')
        for scenario in self.scenarios:
            for frame in scenario.frames:
                ids=[s.node_id for s in frame.states]
                if not set(frame.active_nodes)<=nodes or not set(frame.active_edges)<=edges or not set(ids)<=nodes or len(ids)!=len(set(ids)):
                    raise ValueError('帧引用不存在或重复的对象')
        return self
