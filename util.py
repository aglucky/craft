from sqlalchemy import create_engine
from models import Base, NodeModel, EdgeModel
from langchain_community.embeddings import OllamaEmbeddings
import numpy as np
from sqlalchemy.orm import sessionmaker
from models import Base, NodeModel, EdgeModel
import numpy as np
import subprocess
import time
import json
import random


def getSimilarity(item, goal_vector, embeddings, type="euc"):
    item_vector = embeddings.embed_query(item.result.lower())
    if type == "euc":
        return np.linalg.norm(np.array(goal_vector) - np.array(item_vector))
    else:
        return -abs(np.dot(goal_vector, item_vector) / (
            np.linalg.norm(goal_vector) * np.linalg.norm(item_vector))
        )

def getSimilarityPair(item1, item2, goal_vector, embeddings, type="euc"):
    item_vector = embeddings.embed_query(
        f"the combination of {item1.result.lower()} and {item2.result.lower()}"
    )
    if type == "euc":
        return np.linalg.norm(np.array(goal_vector) - np.array(item_vector))
    else:
        return -abs(np.dot(goal_vector, item_vector) / (
            np.linalg.norm(goal_vector) * np.linalg.norm(item_vector))
        )


def craft(el1, el2):
    curl_command = f"""curl -X GET 'https://neal.fun/api/infinite-craft/pair?first={el1.result}&second={el2.result}' \
-H 'accept: application/json' \
-H 'accept-language: en-US,en;q=0.9' \
-H 'referer: https://neal.fun/infinite-craft/' \
-H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'"""
    time.sleep(0.3)
    try:
        response = subprocess.run(
            curl_command, shell=True, capture_output=True, text=True
        )
        data = json.loads(response.stdout)
        
        if data['result'] == 'Nothing':
            return None
        
        new_node = NodeModel(
            result=data["result"], emoji=data["emoji"], isNew=data["isNew"]
        )
        return new_node
    except Exception:
        return None


def getOrCraft(session, el1, el2):
    existing_edge = (
        session.query(EdgeModel).filter_by(parent1_id=el1.id, parent2_id=el2.id).first()
    )
    if existing_edge:
        child = session.query(NodeModel).filter_by(id=existing_edge.child_id).first()
        return child, existing_edge
    else:
        new_node = craft(el1, el2)
        if new_node:
            duplicate_node = (
                session.query(NodeModel)
                .filter(
                    NodeModel.result == new_node.result,
                    NodeModel.emoji == new_node.emoji,
                )
                .first()
            )
            if not duplicate_node:
                session.add(new_node)
                session.commit()
            else:
                new_node = duplicate_node
            new_edge = EdgeModel(
                parent1_id=el1.id, parent2_id=el2.id, child_id=new_node.id
            )
            session.add(new_edge)
            session.commit()
            return new_node, new_edge

    return None, None


def createSession(echo=False):
    engine = create_engine("sqlite:///graph.db", echo=echo)
    Session = sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(engine)
    return session


def getInitialItems():
    return [
        {"result": "Water", "emoji": "💧", "isNew": False},
        {"result": "Fire", "emoji": "🔥", "isNew": False},
        {"result": "Wind", "emoji": "🌬️", "isNew": False},
        {"result": "Earth", "emoji": "🌍", "isNew": False},
    ]
