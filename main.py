import subprocess
import json
import time
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, NodeModel, EdgeModel

def craft(el1, el2):
    curl_command = f"""curl -X GET 'https://neal.fun/api/infinite-craft/pair?first={el1.result}&second={el2.result}' \
-H 'accept: application/json' \
-H 'accept-language: en-US,en;q=0.9' \
-H 'referer: https://neal.fun/infinite-craft/' \
-H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'"""

    try:
        response = subprocess.run(curl_command, shell=True, capture_output=True, text=True)
        data = json.loads(response.stdout)
        # Create a new NodeModel instance with the response data
        new_node = NodeModel(result=data['result'], emoji=data['emoji'], isNew=data['isNew'], level=max(el1.level, el2.level)+1)
        return new_node
    except Exception as e:
        print(f"Error: {e}")
        return None

def makeRandItems(n, session):
    for _ in range(n):
        # Randomly select two parent nodes from the database
        parent_nodes = session.query(NodeModel).order_by(func.random()).limit(2).all()
        if len(parent_nodes) < 2:
            print("Not enough nodes in the database to select two parents.")
            return
        p1, p2 = parent_nodes

        child = craft(p1, p2)
        if child:
            # Check if the child node already exists
            existing_node = session.query(NodeModel).filter_by(result=child.result, emoji=child.emoji, isNew=child.isNew).first()
            if not existing_node:
                session.add(child)
                session.commit()
                existing_node = child
                
            # Check if edge exists
            new_edge = EdgeModel(parent1_id=p1.id, parent2_id=p2.id, child_id=existing_node.id)
            existing_edge = session.query(EdgeModel).filter_by(parent1_id=p1.id, parent2_id=p2.id, child_id=existing_node.id).first()
            if not existing_edge:
                session.add(new_edge)
                session.commit()
        time.sleep(.3)

def writeGraph(session, filename, maxNodes):
    mermaid_graph = ""
    mermaid_graph += "graph TD\n"
    
    # Query all nodes and create a dictionary for quick access, also sorted by level
    nodes = session.query(NodeModel).order_by(NodeModel.level.asc()).limit(maxNodes).all()
    node_dict = {node.id: node for node in nodes}
    
    # Add nodes to the Mermaid graph using the getName method, considering their level
    for node in nodes:
        style = ".style.fill:red;" if node.isNew else ""
        mermaid_graph += f"    {node.getNode()}[\"{node.getName()}\"{style}]\n"
    
    # Query all edges and add them to the Mermaid graph with intermediate nodes
    edges = session.query(EdgeModel).all()
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


# Check if items exist and add them if they don't
def add_initial_items(session):
    initial_items = [
        {"result": "Water", "emoji": "💧", "isNew": False},
        {"result": "Fire", "emoji": "🔥", "isNew": False},
        {"result": "Wind", "emoji": "🌬️", "isNew": False},
        {"result": "Earth", "emoji": "🌍", "isNew": False},
    ]

    for item in initial_items:
        existing_item = session.query(NodeModel).filter_by(result=item["result"], emoji=item["emoji"]).first()
        if not existing_item:
            new_item = NodeModel(result=item["result"], emoji=item["emoji"], isNew=item["isNew"], level=1)
            session.add(new_item)
    
    session.commit()


# Setup the database connection and session
engine = create_engine('sqlite:///graph.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

# Run Main Code
add_initial_items(session)


makeRandItems(0, session)
file = 'graphs/graph'
writeGraph(session, f'{file}.mmd', 100)
with open(f'{file}.mmd', 'r') as mmd_file, open(f'{file}.md', 'w') as md_file:
    markdown = "# Infinite Craft Chart\n\n```mermaid\n" + mmd_file.read() + "```\n"
    md_file.write(markdown)
subprocess.run(["./render.sh", file], check=True)

