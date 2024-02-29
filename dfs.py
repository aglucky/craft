import random
import graphviz
from util import createSession, getInitialItems, getOrCraft
from models import NodeModel
from tqdm import tqdm

def getStartNodes(session):
    initial_items = getInitialItems()

    nodes = []
    node_levels = {}
    for item in initial_items:
        existing_item = (
            session.query(NodeModel)
            .filter_by(result=item["result"], emoji=item["emoji"], isNew=item["isNew"])
            .first()
        )
        if not existing_item:
            new_item = NodeModel(
                result=item["result"], emoji=item["emoji"], isNew=item["isNew"]
            )
            session.add(new_item)
            session.commit()
            existing_item = new_item
        nodes.append(existing_item)
        node_levels[existing_item.id] = 1
    return nodes, node_levels


def writeGraph(nodes, edges, filename, goal, node_levels):
    dot = graphviz.Digraph("G", node_attr={"shape": "ellipse", "style": "filled"})
    node_dict = {node.id: node for node in nodes}

    for level, nodes_at_level in sorted(
        {
            level: [node_id for node_id, lvl in node_levels.items() if lvl == level]
            for level in set(node_levels.values())
        }.items()
    ):
        with dot.subgraph() as s:
            s.attr(rank="same")
            for node_id in nodes_at_level:
                node = node_dict[node_id]
                if node.result.lower() == goal.lower():
                    color = "#32CD32"  # Bright Green for goal
                elif node.isNew:
                    color = "#B0B0B0"  # New nodes
                else:
                    color = "#F0F0F0"  # Existing nodes
                s.node(
                    str(node_id), label=node.getName(), _attributes={"fillcolor": color}
                )
    # Simplify edge addition with intermediate nodes
    for edge in edges:
        if all(
            node_id in node_dict
            for node_id in [edge.child_id, edge.parent1_id, edge.parent2_id]
        ):
            intermediate_node_id = (
                f"intermediate_{edge.parent1_id}_{edge.parent2_id}_{edge.child_id}"
            )
            dot.node(
                intermediate_node_id,
                shape="point",
                _attributes={"width": ".15", "height": ".15"},
            )
            dot.edges(
                [
                    (str(edge.parent1_id), intermediate_node_id),
                    (str(edge.parent2_id), intermediate_node_id),
                    (intermediate_node_id, str(edge.child_id)),
                ]
            )

    dot.render(filename, format="svg", view=False)
    dot.render(filename, format="pdf", view=False)


session = createSession()
nodes, node_levels = getStartNodes(session)
goal = "Scary"
stack = []
for p1 in nodes:
    for p2 in nodes:
        stack.append((p1, p2))


seen = set([n.id for n in nodes])
edges = set()
file = "graphs/search.gv"

for i in tqdm(range(5000)):
    p1, p2 = stack.pop()
    if ((p1, p2) in seen) or ((p2, p1) in seen):
        continue
    seen.add((p1, p2))
    new_node, edge = getOrCraft(session, p1, p2)

    if new_node and new_node.id not in seen:
        # Mark node as seen
        nodes.append(new_node)
        seen.add(new_node.id)
        edges.add(edge)
        
        parent_levels = [node_levels.get(p1.id, 0), node_levels.get(p2.id, 0)]
        new_node_level = max(parent_levels) + 1
        node_levels[new_node.id] = new_node_level  # Update the node_levels dictionary
        if new_node.result.lower() == goal.lower():
            print(new_node.result)
            break
        for p2 in nodes[:3] + random.sample(nodes, 3):
            stack.append((new_node, p2))
    if i % 100 == 0:
        writeGraph(nodes, edges, f"{file}", goal, node_levels)

writeGraph(nodes, edges, f"{file}", goal, node_levels)
