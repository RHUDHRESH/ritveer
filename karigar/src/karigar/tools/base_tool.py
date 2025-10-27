"""
Base Tool Class - Foundation for all KARIGAR tools
All tools inherit from this base class to ensure consistency
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ToolResult:
    """Result returned by any tool execution"""
    success: bool
    data: Any
    message: str
    execution_time: float
    timestamp: datetime
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }


class BaseTool(ABC):
    """Base class for all KARIGAR tools"""

    def __init__(self, name: str, description: str, required_params: List[str]):
        self.name = name
        self.description = description
        self.required_params = required_params
        self.execution_count = 0
        self.last_execution = None

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters
        Must be implemented by subclasses
        """
        pass

    def validate_params(self, params: Dict) -> bool:
        """Validate that all required parameters are provided"""
        missing = [p for p in self.required_params if p not in params]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")
        return True

    def get_schema(self) -> Dict:
        """Return JSON schema for this tool"""
        return {
            "name": self.name,
            "description": self.description,
            "required_parameters": self.required_params
        }

    def __call__(self, **kwargs) -> ToolResult:
        """Make tool directly callable"""
        import asyncio
        return asyncio.run(self.execute(**kwargs))


class ToolRegistry:
    """Registry for all available tools"""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool"""
        self.tools[tool.name] = tool

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self.tools.get(tool_name)

    def list_tools(self) -> List[Dict]:
        """List all available tools with their schemas"""
        return [tool.get_schema() for tool in self.tools.values()]

    async def execute(self, tool_name: str, **params) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                message=f"Tool '{tool_name}' not found",
                execution_time=0,
                timestamp=datetime.utcnow()
            )

        try:
            tool.validate_params(params)
            return await tool.execute(**params)
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Tool execution failed: {str(e)}",
                execution_time=0,
                timestamp=datetime.utcnow()
            )


# Global registry
tool_registry = ToolRegistry()
