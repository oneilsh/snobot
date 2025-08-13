import duckdb
import os

class SqlDB:
    def __init__(self):
        self.csvs = {
            "concept": "resources/omop_vocab/CONCEPT.csv",
            "concept_ancestor": "resources/omop_vocab/CONCEPT_ANCESTOR.csv",
            "concept_class": "resources/omop_vocab/CONCEPT_CLASS.csv",
            "concept_relationship": "resources/omop_vocab/CONCEPT_RELATIONSHIP.csv",
            "domain": "resources/omop_vocab/DOMAIN.csv",
            "relationship": "resources/omop_vocab/RELATIONSHIP.csv",
            "vocabulary": "resources/omop_vocab/VOCABULARY.csv",
        }

        # note: this is also hardcoded in Makefile
        self.db_path = 'resources/omop_vocab/omop_vocab.duckdb'

        self.init_db()

    def init_db(self):
        """Initialize the DuckDB database and load OMOP vocab data."""
        # check if the database already exists, and if it has any tables
        if os.path.exists(self.db_path):
            conn = duckdb.connect(self.db_path)
            tables = conn.execute("SHOW TABLES;").fetchall()
            if tables:
                print("Database already initialized with tables:", tables)
                return

        # Connect to DuckDB
        conn = duckdb.connect(self.db_path)

        # Create tables and load data
        conn.execute("""
        CREATE TABLE IF NOT EXISTS concept (
            concept_id BIGINT,
            concept_name VARCHAR,
            domain_id VARCHAR,
            vocabulary_id VARCHAR,
            concept_class_id VARCHAR,
            standard_concept VARCHAR,
            concept_code VARCHAR,
            valid_start_date VARCHAR,
            valid_end_date VARCHAR,
            invalid_reason VARCHAR
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS concept_ancestor (
            ancestor_concept_id BIGINT,
            descendant_concept_id BIGINT,
            min_levels_of_separation BIGINT,
            max_levels_of_separation BIGINT
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS concept_class (
            concept_class_id VARCHAR,
            concept_class_name VARCHAR,
            concept_class_concept_id BIGINT
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS concept_relationship (
            concept_id_1 BIGINT,
            concept_id_2 BIGINT,
            relationship_id VARCHAR,
            valid_start_date VARCHAR,
            valid_end_date VARCHAR,
            invalid_reason VARCHAR
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS domain (
            domain_id VARCHAR,
            domain_name VARCHAR,
            domain_concept_id BIGINT
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS relationship (
            relationship_id VARCHAR,
            relationship_name VARCHAR,
            is_hierarchical BOOLEAN,
            defines_ancestry BOOLEAN,
            reverse_relationship_id VARCHAR,
            relationship_concept_id BIGINT
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            vocabulary_id VARCHAR,
            vocabulary_name VARCHAR,
            vocabulary_reference VARCHAR,
            vocabulary_version VARCHAR,
            vocabulary_concept_id BIGINT
        );
        """)


        for table, csv in self.csvs.items():
            conn.execute(f"INSERT INTO {table} SELECT * FROM read_csv_auto('{csv}', sep='\t');")

        conn.commit()
        conn.close()

    def run_query(self, query: str):
        """Run a SQL query against the DuckDB database."""
        conn = duckdb.connect(self.db_path)
        result = conn.execute(query).fetchall()
        conn.close()
        return result