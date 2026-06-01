from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class GenomeModel(Base):
    __tablename__ = 'genomes'

    id = Column(Integer, primary_key=True, index=True)
    generation = Column(Integer, index=True)
    speed = Column(Float)
    size = Column(Float)
    energy_efficiency = Column(Float)
    diet_type = Column(String) # 'herbivore', 'carnivore', 'omnivore'
    fitness = Column(Float)

# Setup SQLite Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./bibitinhos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
