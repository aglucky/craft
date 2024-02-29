import random
from langchain_community.embeddings import OllamaEmbeddings
from sqlalchemy import create_engine, func
from models import Base, NodeModel, EdgeModel
from util import createSession, getOrCraft
import graphviz

def getNodePath(session, filename, node):
    # Create a new directed graph
    dot = graphviz.Digraph(comment='The Highest Item Graph', node_attr={'shape': 'record'})

    q = [(node, 0)]  # Queue now holds tuples of (node, level)
    seen_edges = set()
    node_levels = {}  # Track the level of each node

    while q:
        current_node, level = q.pop(0)
        node_id = current_node.getNode()
        node_label = current_node.getName()
        node_style = 'filled' if current_node.isNew else ''
        node_color = 'red' if current_node.isNew else 'white'
        
        # Add the current node with style and track its level
        dot.node(node_id, label=f"{node_label}", style=node_style, fillcolor=node_color)
        node_levels[node_id] = level
        
        edge = session.query(EdgeModel).filter(EdgeModel.child_id == current_node.id).first()
        if edge and edge not in seen_edges:
            parent1 = session.query(NodeModel).filter(NodeModel.id == edge.parent1_id).first()
            parent2 = session.query(NodeModel).filter(NodeModel.id == edge.parent2_id).first()
            if not (parent1 and parent2):
                continue
            # Create an intermediate node for each edge
            intermediate_node_id = f"intermediate_{edge.parent1_id}_{edge.parent2_id}_{edge.child_id}"
            dot.node(intermediate_node_id, shape='point')  # Represented as a small circle or dot
            
            # Connect parents to the intermediate node, then to the child
            dot.edge(parent1.getNode(), intermediate_node_id)
            dot.edge(parent2.getNode(), intermediate_node_id)
            dot.edge(intermediate_node_id, node_id)
            
            # Add parents to q with incremented level
            q.append((parent1, level + 1))
            q.append((parent2, level + 1))
            seen_edges.add(edge)
    
    # Save the graph to a file
    dot.render(filename, view=False)


session = createSession()
discovered_nodes = session.query(NodeModel).filter_by(isNew=True).all()
for node in discovered_nodes:
    print(f"Discovered Node: {node.getName()}")

node = random.choice(discovered_nodes)
getNodePath(session, 'graphs/discover', node)


