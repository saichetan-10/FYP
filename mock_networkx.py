"""Mock NetworkX implementation for systems without networkx installed."""

class DiGraph:
    """Mock directed graph implementation."""

    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, node_id, **attrs):
        """Add a node to the graph."""
        self.nodes[node_id] = attrs

    def add_edge(self, from_node, to_node, **attrs):
        """Add an edge to the graph."""
        self.edges.append((from_node, to_node, attrs))

    def nodes(self):
        """Return nodes."""
        return self.nodes.keys()

    def edges(self):
        """Return edges."""
        return self.edges

    def successors(self, node):
        """Return successors of a node."""
        return [edge[1] for edge in self.edges if edge[0] == node]

    def predecessors(self, node):
        """Return predecessors of a node."""
        return [edge[0] for edge in self.edges if edge[1] == node]

    def get_node_attributes(self, node, attr):
        """Get node attributes."""
        return self.nodes.get(node, {}).get(attr, None)

    def has_node(self, node):
        """Check if node exists."""
        return node in self.nodes

    def has_edge(self, from_node, to_node):
        """Check if edge exists."""
        return any(edge[0] == from_node and edge[1] == to_node for edge in self.edges)