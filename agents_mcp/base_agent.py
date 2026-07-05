from abc import ABC, abstractmethod
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata


class BaseAgent(ABC):
    def __init__(self, metadata: AgentMetadata):
        self.metadata = metadata
        self.name = metadata.name

    @abstractmethod
    def run(self, agent_input: AgentInput) -> AgentOutput:
        pass

    def success_response(self, data: dict, message: str = None) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            success=True,
            data=data,
            message=message
        )

    def error_response(self, error: str, data: dict = None) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            success=False,
            data=data or {},
            error=error
        )