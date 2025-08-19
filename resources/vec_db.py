from sentence_transformers import SentenceTransformer
from models.db import VecDBHit
import os
import pandas as pd
import chromadb
from chromadb.config import Settings


class VecDB:
    def __init__(self):
        self.embedding_model_name = "intfloat/e5-small-v2"
        # strings should be prefixed with "query:" for intfloat models
        self.embedding_prefix = "query:" if "intfloat" in self.embedding_model_name else ""
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        self.source_concept_file = "resources/omop_vocab/CONCEPT.csv"
        # ChromaDB persistent storage directory
        self.chroma_db_path = "resources/omop_vocab/chroma_db"
        self.collection_name = "omop_concepts"

        self.init_chroma_db()
        self.client = chromadb.PersistentClient(path=self.chroma_db_path)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)


    def init_chroma_db(self):
        """Initialize ChromaDB with concept embeddings."""
        if not os.path.exists(self.source_concept_file):
            raise FileNotFoundError(f"Source file {self.source_concept_file} not found.")
        
        # Create ChromaDB client to check if collection exists and has data
        temp_client = chromadb.PersistentClient(path=self.chroma_db_path)
        try:
            collection = temp_client.get_collection(name=self.collection_name)
            if collection.count() > 0:
                print(f"ChromaDB collection '{self.collection_name}' already exists with {collection.count()} concepts.")
                return
        except Exception:
            # Collection doesn't exist yet, we'll create it
            pass

        print("Loading concepts...")
        df = pd.read_csv(self.source_concept_file, sep="\t", dtype=str, keep_default_na=False, na_values=[""])

        print("Generating embeddings and adding to ChromaDB...")
        collection = temp_client.get_or_create_collection(name=self.collection_name)
        
        max_records = len(df)
        batch_size = 256
        
        for i in range(0, max_records, batch_size):
            batch = df.iloc[i:i + batch_size]
            
            # Generate embeddings using your existing logic
            embeddings = self.embedding_model.encode(
                [self.embedding_prefix + concept_name for concept_name in batch["concept_name"].tolist()],
                convert_to_tensor=True,
                normalize_embeddings=True,
            )
            
            # Convert embeddings to list format for ChromaDB
            # embeddings is a 2D tensor (batch_size, embedding_dim), convert to list of lists
            embeddings_list = embeddings.cpu().numpy().tolist()
            
            # Prepare data for ChromaDB
            documents = batch["concept_name"].tolist()
            metadatas = [
                {
                    "domain_id": row["domain_id"],
                    "vocabulary_id": row["vocabulary_id"], 
                    "concept_class_id": row["concept_class_id"],
                    "standard_concept": row["standard_concept"],
                    "concept_code": row["concept_code"]
                }
                for _, row in batch.iterrows()
            ]
            ids = batch["concept_id"].tolist()
            
            # Add to ChromaDB
            collection.add(
                documents=documents,
                embeddings=embeddings_list,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"Processed {i + len(batch)} out of {max_records} concepts ({(i + len(batch)) / max_records * 100:.2f}%).")

        print(f"ChromaDB initialization complete with {collection.count()} concepts.")
    

    def query(self, text, top_k=5) -> list[VecDBHit]:
        """Query ChromaDB for similar OMOP concepts."""
        if self.collection is None:
            raise ValueError("ChromaDB collection not initialized.")
        
        # Generate query embedding using your existing logic
        query_embedding = self.embedding_model.encode(
            [self.embedding_prefix + text],
            convert_to_tensor=True,
            normalize_embeddings=True,
        ).cpu().numpy().tolist()[0]  # Get the first (and only) embedding from the batch

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Convert results to VecDBHit format
        hits = []
        for i in range(len(results['ids'][0])):
            concept_id = results['ids'][0][i]
            concept_name = results['documents'][0][i]
            # ChromaDB returns distances, but we want similarity scores
            # Convert distance to similarity (higher is better)
            distance = results['distances'][0][i]
            hits.append(VecDBHit(
                search_string=text, 
                concept_id=concept_id, 
                concept_name=concept_name, 
                distance=float(distance)
            ))
        
        return hits