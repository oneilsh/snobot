from sentence_transformers import SentenceTransformer
import os
import pandas as pd
import faiss
import numpy as np

class VecDB:
    def __init__(self):
        self.embedding_model_name = "intfloat/e5-small-v2"
        # strings should be prefixed with "query:" for intfloat models
        self.embedding_prefix = "query:" if "intfloat" in self.embedding_model_name else ""
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        self.source_concept_file = "resources/omop_vocab/CONCEPT.csv"
        # note: these are also hardcoded in Makefile
        self.embedding_dest_file = "resources/omop_vocab/embeddings.csv"
        self.faiss_index_file = "resources/omop_vocab/faiss.index"

        self.init_embeddings()
        self.init_faiss_index()

        self.concept_df = self.load_concepts()
        self.faiss_index = self.load_faiss_index()


    def init_embeddings(self):
        """Initialize concept embeddings."""
        if not os.path.exists(self.source_concept_file):
            raise FileNotFoundError(f"Source file {self.source_concept_file} not found.")
        
        if os.path.exists(self.embedding_dest_file):
            print(f"Embeddings file {self.embedding_dest_file} already exists.")
            return

        print("Loading concepts...")
        df = pd.read_csv(self.source_concept_file, sep="\t", dtype=str, keep_default_na=False, na_values=[""])


        print("Generating embeddings...")
        with open(self.embedding_dest_file, "w") as f:
            f.write("concept_id\tconcept_name\tconcept_embedding\n")
            max = len(df)
            #max = 4196
            for i in range(0, max, 256):
                batch = df.iloc[i:i + 256]
                embeddings = self.embedding_model.encode(
                    [self.embedding_prefix + concept_name for concept_name in batch["concept_name"].tolist()],
                    convert_to_tensor=True,
                    normalize_embeddings=True,
                )
                for j, embedding in enumerate(embeddings):
                    f.write(f"{batch['concept_id'].iloc[j]}\t{batch['concept_name'].iloc[j]}\t{embedding.cpu().numpy().tolist()}\n")

                print(f"Processed {i + len(batch)} out of {len(df)} concepts ({(i + len(batch)) / len(df) * 100:.2f}%).")

    def init_faiss_index(self):
        """Initialize the FAISS index for concept embeddings."""
        if os.path.exists(self.faiss_index_file):
            print(f"FAISS index file {self.faiss_index_file} already exists.")
            return
        
        if not os.path.exists(self.embedding_dest_file):
            raise FileNotFoundError(f"Embeddings file {self.embedding_dest_file} not initialized.")

        print("Loading embeddings from file...")
     
        dimension = 0
        with open(self.embedding_dest_file, "r") as f:
            header = f.readline()
            first_line = f.readline()
            first_embedding = eval(first_line.split("\t")[2])
            dimension = len(first_embedding)

        index = faiss.IndexFlatIP(dimension)
        
        batch_size = 10000
        print("Counting total concepts...")
        total_concepts = sum(1 for _ in open(self.embedding_dest_file)) - 1  # Exclude header
        # Add embeddings to the FAISS index
        print(f"Adding embeddings to FAISS index, total concepts: {total_concepts}, batch size: {batch_size}...")
        for batch in pd.read_csv(self.embedding_dest_file, sep="\t", dtype=str, chunksize=batch_size):
            batch["concept_embedding"] = batch["concept_embedding"].apply(eval)
            embeddings = np.vstack(batch["concept_embedding"].values).astype("float32")
            index.add(embeddings)
            print(f"Added {index.ntotal} embeddings to FAISS index ({100 * index.ntotal / total_concepts:.2f}%).")

        faiss.write_index(index, self.faiss_index_file)
        print(f"FAISS index created and saved to {self.faiss_index_file}.")

    def load_concepts(self):
        """Load concept embeddings from file."""
        if not os.path.exists(self.embedding_dest_file):
            raise FileNotFoundError(f"Embeddings file {self.embedding_dest_file} not found. Please run init_embeddings() first.")

        df = pd.read_csv(self.embedding_dest_file, sep="\t", dtype={"concept_id": str, "concept_name": str})
        return df
    
    def load_faiss_index(self):
        """Load the FAISS index from file."""
        if not os.path.exists(self.faiss_index_file):
            raise FileNotFoundError(f"FAISS index file {self.faiss_index_file} not initialized.")
        
        print("Loading FAISS index from file...")
        index = faiss.read_index(self.faiss_index_file)
        print(f"FAISS index loaded with {index.ntotal} concepts.")
        return index
    

    def query(self, text, top_k=5):
        """Query the FAISS index for similar OMOP concepts."""
        if self.faiss_index is None or self.concept_df is None:
            raise ValueError("FAISS index not initialized.")
        
        query_embedding = self.embedding_model.encode(
            [self.embedding_prefix + text],
            convert_to_tensor=True,
            normalize_embeddings=True,
        ).cpu().numpy().astype("float32")

        distances, indices = self.faiss_index.search(query_embedding, top_k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            concept_id = self.concept_df.iloc[idx]["concept_id"]
            concept_name = self.concept_df.iloc[idx]["concept_name"]
            results.append((concept_id, concept_name, float(dist)))
        
        return results