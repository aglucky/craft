from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class NodeModel(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    result = Column(String, nullable=False)
    emoji = Column(String, nullable=False)
    isNew = Column(Boolean, nullable=False)

    def getName(self):
        result_modified = self.result.replace(' ', '_').replace("'", "")
        return f"{result_modified}{self.emoji}"

    def getNode(self):
        result_modified = self.result.replace(' ', '_').replace("'", "")
        return f"{result_modified}"
    
    def __hash__(self):
        # This assumes that the combination of result, emoji, and isNew
        # uniquely identifies a Node. Adjust as necessary.
        return hash((self.result, self.emoji, self.isNew))

    def __eq__(self, other):
        if not isinstance(other, NodeModel):
            return NotImplemented
        return (self.result, self.emoji, self.isNew) == (other.result, other.emoji, other.isNew)
    
    def __lt__(self, other):
        if not isinstance(other, NodeModel):
            return NotImplemented
        return self.level < other.level or (self.level == other.level and self.result < other.result)

    def __le__(self, other):
        if not isinstance(other, NodeModel):
            return NotImplemented
        return self.level < other.level or (self.level == other.level and self.result <= other.result)

    def __gt__(self, other):
        if not isinstance(other, NodeModel):
            return NotImplemented
        return self.level > other.level or (self.level == other.level and self.result > other.result)

    

class EdgeModel(Base):
    __tablename__ = 'edges'
    id = Column(Integer, primary_key=True, autoincrement=True)
    parent1_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    parent2_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    child_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
        
    def __str__(self):
        return f"Edge from parent1 ID: {self.parent1_id}, parent2 ID: {self.parent2_id} to child ID: {self.child_id}"
