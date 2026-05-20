"""Mock LangGraph implementation for basic functionality."""

from typing import Any, Dict, List, Callable, Optional
import asyncio


class StateGraph:
    """Mock StateGraph."""

    def __init__(self, state_class):
        self.state_class = state_class
        self.nodes = {}
        self.edges = []

    def add_node(self, name: str, func: Callable):
        """Add a node."""
        self.nodes[name] = func

    def add_edge(self, from_node: str, to_node: str):
        """Add an edge."""
        self.edges.append((from_node, to_node))

    def set_entry_point(self, node: str):
        """Set entry point."""
        self.entry_point = node

    def set_finish_point(self, node: str):
        """Set finish point."""
        self.finish_point = node

    def compile(self):
        """Compile the graph."""
        return MockCompiledGraph(self)


class MockCompiledGraph:
    """Mock compiled graph."""

    def __init__(self, graph):
        self.graph = graph

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Mock invoke."""
        # Simple sequential execution
        current_state = state.copy()

        for node_name, func in self.graph.nodes.items():
            if asyncio.iscoroutinefunction(func):
                current_state = await func(current_state)
            else:
                current_state = func(current_state)

        return current_state