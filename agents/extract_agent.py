from pydantic_ai import Agent, RunContext
from pydantic_ai.settings import ModelSettings
from ui.utils import OMOP_DOMAINS, OMOP_DOMAINS_LITERAL
from resources.st_resources import sql_db, vec_db, logger
from models import Mention, MentionList, AgentCodedConcept, FullCodedConcept, EnhancedConcept, ConceptRelation, ConceptCollection
import json
import dotenv
import pprint
import streamlit as st
from agents.strings import examples
from typing import Optional

dotenv.load_dotenv(override=True)


def extract_and_code_mentions(text: str, status_widget) -> list[FullCodedConcept]:
    """Given an input text, returns a list of strings representing potnentially codable SNOMED concepts or synonyms to identify."""

    sub_agent = Agent("gpt-4.1", 
                      system_prompt=f"You are a helpful assistant that extracts potential SNOMED concepts or synonyms from clinical text. When identifying codable spans, consider the following examples and guidelines: {examples}. Note that your job is simple to identify text spans in need of coding; a subsequent process will be used to identifying matching concepts.",
                      output_type=MentionList,
                      model_settings = ModelSettings(temperature=0.0))

    status_widget.update(label="Identifying mentions...")
    run_result = sub_agent.run_sync("Please identify potential SNOMED concepts in the following text:\n\n" + text)
    mentions = run_result.output.mentions
    # remove duplicates
    mentions_str = set([mention.mention_str for mention in mentions])

    coded_concepts: list[FullCodedConcept] = []
    for found_mention in mentions_str:
        status_widget.update(label=f"Coding '{found_mention}'...")
        # todo: this is slow, we can update the status box to show progress
        coded_concept = code_mention(found_mention, text, status_widget)
        coded_concepts.append(coded_concept)

    return coded_concepts


def get_concept_ids_context(concept_ids: list[str]) -> ConceptCollection:
    """Get context for a list of concept IDs, including hierarchy information."""
    # Get mappings to standard concepts
    sql_query = f"SELECT concept_id_1, concept_id_2 FROM concept_relationship WHERE concept_id_1 IN ({','.join(concept_ids)}) AND relationship_id = 'Maps to'"
    mapping_results = sql_db.run_query(sql_query)
    
    # Create a mapping dict: original_id -> standard_id
    concept_mappings = {str(row[0]): str(row[1]) for row in mapping_results}
    
    # For each original concept, use the standard mapping if available, otherwise use the original
    final_concept_ids = []
    for concept_id in concept_ids:
        if concept_id in concept_mappings:
            final_concept_ids.append(concept_mappings[concept_id])  # Use standard
        else:
            final_concept_ids.append(concept_id)  # Use original (no mapping available)
    
    # Remove duplicates while preserving order
    final_concept_ids = list(dict.fromkeys(final_concept_ids))
    
    # Get concept details
    sql_query = f"SELECT concept_id, concept_name, domain_id, vocabulary_id, concept_code, standard_concept FROM concept WHERE concept_id IN ({','.join(final_concept_ids)})"
    hits_details = sql_db.run_query(sql_query)
    
    # Build enhanced concepts with hierarchy information
    enhanced_concepts = []
    for row in hits_details:
        concept_id, concept_name, domain_id, vocabulary_id, concept_code, standard_concept = row
        
        # Get parent concepts (concepts that this concept "Is a" type of)
        sql_query = f"SELECT concept_relationship.concept_id_2, concept.concept_name FROM concept_relationship INNER JOIN concept ON concept_relationship.concept_id_2 = concept.concept_id WHERE concept_id_1 = {concept_id} AND relationship_id = 'Is a'"
        parents_data = sql_db.run_query(sql_query)
        parent_concepts = [ConceptRelation(concept_id=str(parent[0]), concept_name=str(parent[1])) for parent in parents_data] if parents_data else None
        
        # Get child concepts (concepts that are "Is a" type of this concept)
        sql_query = f"SELECT concept_relationship.concept_id_1, concept.concept_name FROM concept_relationship INNER JOIN concept ON concept_relationship.concept_id_1 = concept.concept_id WHERE concept_id_2 = {concept_id} AND relationship_id = 'Is a'"
        children_data = sql_db.run_query(sql_query)
        child_concepts = [ConceptRelation(concept_id=str(child[0]), concept_name=str(child[1])) for child in children_data] if children_data else None
        
        enhanced_concept = EnhancedConcept(
            concept_id=str(concept_id),
            concept_name=str(concept_name),
            domain_id=str(domain_id),
            vocabulary_id=str(vocabulary_id),
            concept_code=str(concept_code),
            standard=standard_concept == 'S',
            parent_concepts=parent_concepts,
            child_concepts=child_concepts
        )
        enhanced_concepts.append(enhanced_concept)
    
    return ConceptCollection(
        concepts=enhanced_concepts,
        total_count=len(enhanced_concepts)
    )


def get_hits_context(found_mention) -> ConceptCollection:
    """Get concept candidates for a mention from vector database."""
    hits = vec_db.query(found_mention, 10) 
    concept_ids = [hit.concept_id for hit in hits]

    concept_collection = get_concept_ids_context(concept_ids)
    concept_collection.search_query = found_mention
    
    return concept_collection

def code_mention(found_mention: str, context: str, status_widget) -> FullCodedConcept:
    """Given a found mention and the context, return the coded concept."""

    status_widget.update(label=f"Coding '{found_mention}'... querying databases...")

    concept_collection = get_hits_context(found_mention)

    sub_agent = Agent("gpt-4.1", 
                      system_prompt=f"You are a helpful assistant that identifies the best fitting OMOP concept from a list of candidates. Given a context and a YAML-structured list of candidate OMOP concepts with hierarchical information, return the concept_id, concept_name, and whether it is negated in the context. If the candidates available are a poor fit due to phrasing, you can use the search_string tool to find better candidates with a more appropriate phrasing. You should also explore the hierarchy as necessary to identify the best fitting concepts. Use the following examples and guidelines to guide your search: {examples}",
                      output_type=AgentCodedConcept,
                      model_settings = ModelSettings(temperature=0.0))

    @sub_agent.tool
    async def string_search(ctx: RunContext, query: str) -> str:
        """Search the database for matching concepts by name. Useful when no current candidate seems a good fit but an alternative name can be identified based on the context. If known, search for an OMOP concept_name, or similar medical terminology."""
        status_widget.update(label=f"Coding '{found_mention}'... searching for alternative phrasing '{query}'...")
        search_results = get_hits_context(query)
        return search_results.to_yaml()

    @sub_agent.tool
    async def get_concept_context(ctx: RunContext, concept_ids: list[str]) -> str:
        """Retrieve context about a list of concept_ids in the form of parents and children concepts. Useful to identify potential more-general or more-specific concepts."""
        status_widget.update(label=f"Coding '{found_mention}'... retrieving concept context...")
        context_results = get_concept_ids_context(concept_ids)
        return context_results.to_yaml()

    yaml_candidates = concept_collection.to_yaml()
    instructions = f"From the following context, identify the best fitting OMOP concept and whether it is negated in the context:\n\nContext:\n```\n{context}\n```\n\nCandidate Concepts (YAML format):\n```yaml\n{yaml_candidates}\n```"

    run_result = sub_agent.run_sync(instructions).output
    
    # Try to map to standard concept, fall back to original if no mapping exists
    original_concept_id = run_result.concept_id
    sql_query = f"SELECT concept_id_2 FROM concept_relationship WHERE concept_id_1 = {original_concept_id} AND relationship_id = 'Maps to'"
    query_result = sql_db.run_query(sql_query)
    
    if query_result:
        # Found a standard mapping, use it
        agent_picked_concept_id = query_result[0][0]
        status_widget.update(label=f"Coding '{found_mention}'... mapped to standard concept...")
    else:
        # No standard mapping found, use the original concept
        agent_picked_concept_id = original_concept_id
        status_widget.update(label=f"Coding '{found_mention}'... using non-standard concept (no mapping available)...")

    sql_query = f"SELECT concept_id, concept_name, domain_id, vocabulary_id, concept_code, standard_concept FROM concept WHERE concept_id = {agent_picked_concept_id}"

    query_result = sql_db.run_query(sql_query)
    concept_data = query_result[0]  # Get the first row (tuple/list)
     
     # Manually unpack the tuple into the dataclass
    coded_concept = FullCodedConcept(
         mention_str=found_mention,
         concept_id=str(concept_data[0]),
         concept_name=str(concept_data[1]),
         domain_id=str(concept_data[2]),
         vocabulary_id=str(concept_data[3]),
         concept_code=str(concept_data[4]),
         standard=concept_data[5] == 'S',  # Convert 'S' to True, everything else to False
         negated=run_result.negated
     )

    return coded_concept