from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine, Column, Integer, Text, String
from sqlalchemy.orm import declarative_base, sessionmaker
from sentence_transformers import SentenceTransformer

# DB 연결
engine = create_engine("postgresql+psycopg2://user:password@localhost:5432/yourdb")
Base = declarative_base()

class WelfareDoc(Base):
    __tablename__ = "welfare_docs"
    id = Column(String, primary_key=True)
    source = Column(String)
    content = Column(Text)
    embedding = Column(Vector(768))  # 모델 차원에 맞게 조정

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# 임베딩 + 저장
model = SentenceTransformer("jhgan/ko-sroberta-multitask")

for r in records:
    emb = model.encode(r["content"]).tolist()
    session.add(WelfareDoc(id=r["id"], source=r["source"], content=r["content"], embedding=emb))

session.commit()
