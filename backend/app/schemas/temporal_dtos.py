from dataclasses import dataclass


@dataclass
class ProjectDetails:
    id: str


@dataclass
class EnvironmentDetails:
    id: str
    project_id: str
    name: str
