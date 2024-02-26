from langchain_community.embeddings import OllamaEmbeddings
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, NodeModel, EdgeModel
import heapq
import numpy as np
import subprocess
import time
import json
import random
from util import getOrCraft, getSimilarity, getSimilarityPair

def getStartNodes(session, goal_vector, embeddings):
    initial_items = [
        {"result": "Water", "emoji": "💧", "isNew": False},
        {"result": "Fire", "emoji": "🔥", "isNew": False},
        {"result": "Wind", "emoji": "🌬️", "isNew": False},
        {"result": "Earth", "emoji": "🌍", "isNew": False},
    ]
    
    nodes = []
    for item in initial_items:
        existing_item = session.query(NodeModel).filter_by(result=item["result"], emoji=item["emoji"], isNew=item["isNew"]).first()
        if not existing_item:
            new_item = NodeModel(result=item["result"], emoji=item["emoji"], isNew=item["isNew"], level=1)
            session.add(new_item)
            session.commit()
            existing_item = new_item
        sim = getSimilarity(existing_item, goal_vector, embeddings)
        heapq.heappush(nodes, (-sim, existing_item))
    return nodes


def writeGraph(heap, edges, filename, goal):
    mermaid_graph = ""
    mermaid_graph += "graph TD\n"
    
    # Query all nodes and create a dictionary for quick access, also sorted by level
    nodes = [x[1] for x in heap]
    node_dict = {node.id: node for node in nodes}
    
    # Add nodes to the Mermaid graph using the getName method, considering their level
    for node in nodes:
        style = "fill:#fff" if node.isNew else ""
        style = "fill:#f90" if node.result.lower() == goal.lower() else style
        mermaid_graph += f"    {node.getNode()}[\"{node.getName()}\"]\n"
        if style:
             mermaid_graph += f"    style {node.getNode()} {style}\n"

            
    
    # Query all edges and add them to the Mermaid graph with intermediate nodes
    for edge in edges:
        edge_ids = [edge.child_id, edge.parent1_id, edge.parent2_id]
        if not all(node_id in node_dict for node_id in edge_ids):
            continue
        parent1 = node_dict.get(edge.parent1_id)
        parent2 = node_dict.get(edge.parent2_id)
        child = node_dict.get(edge.child_id)
        
        # Create an intermediate node for each edge, considering the level for placement
        intermediate_node_id = f"intermediate_{edge.parent1_id}_{edge.parent2_id}_{edge.child_id}"
        # Intermediate nodes are visually represented as small circles or dots
        mermaid_graph += f"    {intermediate_node_id}(( ))\n"
        
        # Connect parents to the intermediate node, then to the child
        mermaid_graph += f"    {parent1.getNode()} --> {intermediate_node_id}\n"
        mermaid_graph += f"    {parent2.getNode()} --> {intermediate_node_id}\n"
        mermaid_graph += f"    {intermediate_node_id} --> {child.getNode()}\n"
    
    with open(filename, 'w') as file:
        file.write(mermaid_graph)



engine = create_engine('sqlite:///graph.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

embeddings = OllamaEmbeddings(model="nomic-embed-text")
goal = "Amazon"
goal_vector = embeddings.embed_query(goal.lower())

nodes = getStartNodes(session, goal_vector, embeddings)
heap = []
for p1 in nodes:
    for p2 in nodes:
        sim = getSimilarityPair(p1[1], p2[1], goal_vector, embeddings)
        heapq.heappush(heap, (-sim, p1[1], p2[1]))
        

seen = set()
edges = set()
for _ in range(500):
    sim, p1, p2 = heapq.heappop(heap)
    if ((p1, p2) in seen) or ((p2, p1) in seen):
        continue
    seen.add((p1, p2))
    new_node, edge = getOrCraft(session, p1, p2)
    
    if new_node:
        sim = getSimilarity(new_node, goal_vector, embeddings)
        heapq.heappush(nodes, (-sim, new_node))
        edges.add(edge)
        if new_node.result.lower() == goal.lower():
            print(new_node.result)
            break
        
        for new_par in heapq.nsmallest(min(len(heap), 8), heap):
            sim = getSimilarityPair(new_node, new_par[1], goal_vector, embeddings)
            heapq.heappush(heap, (-sim, new_node, new_par[1]))
            


file = 'graphs/search'
writeGraph(nodes, edges, f"{file}.mmd", goal)
with open(f'{file}.mmd', 'r') as mmd_file, open(f'{file}.md', 'w') as md_file:
    markdown = "# Infinite Craft Chart\n\n```mermaid\n" + mmd_file.read() + "```\n"
    md_file.write(markdown)
subprocess.run(["./render.sh", file], check=True)
