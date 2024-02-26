from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, NodeModel, EdgeModel
import subprocess

def highestItemGraph(session, filename):
    mermaid_graph = "graph TD\n"
    
    # Query all nodes and create a dictionary for quick access, also sorted by level
    node = session.query(NodeModel).order_by(NodeModel.level.desc()).first()
    q = [node]
    seen_edges = set()
    while q:
        current_node = q.pop(0)
        style = ".style.fill:red;" if current_node.isNew else ""
        mermaid_graph += f"    {current_node.getNode()}[\"{current_node.getName()}\"{style}]\n"
        
        edge = session.query(EdgeModel).filter(EdgeModel.child_id == current_node.id).first()
        if edge and edge not in seen_edges:
            parent1 = session.query(NodeModel).filter(NodeModel.id == edge.parent1_id).first()
            parent2 = session.query(NodeModel).filter(NodeModel.id == edge.parent2_id).first()
            # Create an intermediate node for each edge, considering the level for placement
            intermediate_node_id = f"intermediate_{edge.parent1_id}_{edge.parent2_id}_{edge.child_id}"
            # Intermediate nodes are visually represented as small circles or dots
            mermaid_graph += f"    {intermediate_node_id}(( ))\n"
            # Connect parents to the intermediate node, then to the child
            mermaid_graph += f"    {parent1.getNode()} --> {intermediate_node_id}\n"
            mermaid_graph += f"    {parent2.getNode()} --> {intermediate_node_id}\n"
            mermaid_graph += f"    {intermediate_node_id} --> {current_node.getNode()}\n"
            # Add parents to q
            q.append(parent1)
            q.append(parent2)
            seen_edges.add(edge)
            
    with open(filename, 'w') as file:
        file.write(mermaid_graph)

# Setup the database connection and session
engine = create_engine('sqlite:///graph.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

file = 'graphs/viz'
highestItemGraph(session, f'{file}.mmd')
with open(f'{file}.mmd', 'r') as mmd_file, open(f'{file}.md', 'w') as md_file:
    markdown = "# Infinite Craft Chart\n\n```mermaid\n" + mmd_file.read() + "```\n"
    md_file.write(markdown)
subprocess.run(["./render.sh", file], check=True)

