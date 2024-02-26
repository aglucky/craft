from langchain_community.embeddings import OllamaEmbeddings
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, NodeModel, EdgeModel
import heapq
import numpy as np
import subprocess
import graphviz
from util import createSession, getOrCraft, getSimilarity, getSimilarityPair


def getStartNodes(session, goal_vector, embeddings):
    initial_items = [
        {"result": "Water", "emoji": "💧", "isNew": False},
        {"result": "Fire", "emoji": "🔥", "isNew": False},
        {"result": "Wind", "emoji": "🌬️", "isNew": False},
        {"result": "Earth", "emoji": "🌍", "isNew": False},
    ]
    
    nodes = []
    node_levels = {}  # New dictionary to keep track of node levels
    for item in initial_items:
        existing_item = session.query(NodeModel).filter_by(result=item["result"], emoji=item["emoji"], isNew=item["isNew"]).first()
        if not existing_item:
            new_item = NodeModel(result=item["result"], emoji=item["emoji"], isNew=item["isNew"])
            session.add(new_item)
            session.commit()
            existing_item = new_item
        sim = getSimilarity(existing_item, goal_vector, embeddings)
        heapq.heappush(nodes, (-sim, existing_item))
        node_levels[existing_item.id] = 1  # Assign level 1 to initial nodes
    return nodes, node_levels


def writeGraph(heap, edges, filename, goal, node_levels):
    dot = graphviz.Digraph('G', node_attr={'shape': 'ellipse', 'style': 'filled'})
    node_dict = {node.id: node for _, node in heap}
    sim_dict = {node.id: -sim for sim, node in heap}

    for level, nodes_at_level in sorted({level: [node_id for node_id, lvl in node_levels.items() if lvl == level] for level in set(node_levels.values())}.items()):
        with dot.subgraph() as s:
            s.attr(rank='same')
            for node_id in nodes_at_level:
                node = node_dict[node_id]
                if node.result.lower() == goal.lower():
                    color = "#32CD32"  # Bright Green for goal
                elif node.isNew:
                    color = "#B0B0B0"  # New nodes
                else:
                    color = "#F0F0F0"  # Existing nodes
                s.node(str(node_id), label=node.getName(), _attributes={'fillcolor': color})
    # Simplify edge addition with intermediate nodes
    for edge in edges:
        if all(node_id in node_dict for node_id in [edge.child_id, edge.parent1_id, edge.parent2_id]):
            intermediate_node_id = f"intermediate_{edge.parent1_id}_{edge.parent2_id}_{edge.child_id}"
            dot.node(intermediate_node_id, shape='point', _attributes={'width': '.15', 'height': '.15'})
            dot.edges([(str(edge.parent1_id), intermediate_node_id), (str(edge.parent2_id), intermediate_node_id), (intermediate_node_id, str(edge.child_id))])

    dot.render(filename, format='svg', view=False)
    dot.render(filename, format='pdf', view=False)

session = createSession()

embeddings = OllamaEmbeddings(model="nomic-embed-text")
goal = "Human"
goal_vector = embeddings.embed_query(goal.lower())

nodes, node_levels = getStartNodes(session, goal_vector, embeddings)
# Assuming the initial setup and getStartNodes function remain unchanged

heap = []
for p1 in nodes:
    for p2 in nodes:
        sim = getSimilarityPair(p1[1], p2[1], goal_vector, embeddings)
        heapq.heappush(heap, (-sim, p1[1], p2[1]))

seen = set()
edges = set()
node_levels = {node.id: 1 for _, node in nodes}  # Initialize node levels for starting nodes

for _ in range(500):
    sim, p1, p2 = heapq.heappop(heap)
    if ((p1, p2) in seen) or ((p2, p1) in seen):
        continue
    seen.add((p1, p2))
    new_node, edge = getOrCraft(session, p1, p2)
    
    if new_node:
        sim = getSimilarity(new_node, goal_vector, embeddings)
        heapq.heappush(nodes, (-sim, new_node))
        if new_node.id not in node_levels:
            edges.add(edge)
            # Determine the new node's level based on its parents
            parent_levels = [node_levels.get(p1.id, 0), node_levels.get(p2.id, 0)]
            new_node_level = max(parent_levels) + 1
            node_levels[new_node.id] = new_node_level  # Update the node_levels dictionary
            
        if new_node.result.lower() == goal.lower():
            print(new_node.result)
            break
        
        for new_par in heapq.nsmallest(min(len(heap), 8), heap):
            sim = getSimilarityPair(new_node, new_par[1], goal_vector, embeddings)
            heapq.heappush(heap, (-sim, new_node, new_par[1]))

file = 'graphs/search.gv'
writeGraph(nodes, edges, f"{file}", goal, node_levels)
