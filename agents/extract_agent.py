from pydantic_ai import Agent, RunContext
from pydantic_ai.settings import ModelSettings
from ui.utils import OMOP_DOMAINS, OMOP_DOMAINS_LITERAL
from resources.st_resources import sql_db, vec_db, logger
from models import Mention, MentionList, AgentCodedConcept, FullCodedConcept, EnhancedConcept, ConceptRelation, ConceptCollection, ExtractionLogger
from models.model_config import DEFAULT_MODEL
import json
import dotenv
import pprint
import streamlit as st
from agents.strings import examples
from typing import Optional, Tuple
import uuid
import time

dotenv.load_dotenv(override=True)


def extract_and_code_mentions(text: str, status_widget) -> Tuple[list[FullCodedConcept], ExtractionLogger]:
    """Given an input text, returns a list of coded concepts and the extraction log."""

    process_id = str(uuid.uuid4())[:8]
    extraction_logger = ExtractionLogger(text, process_id)
    
    step_id = extraction_logger.start_step("mention_id", "mention_identification", "Identifying potential SNOMED mentions")
    
    sub_agent = Agent(DEFAULT_MODEL, 
                      system_prompt=f"You are a helpful assistant that extracts potential SNOMED concepts or synonyms from clinical text. When identifying codable spans, consider the following examples and guidelines: {examples}. Note that your job is simple to identify text spans in need of coding; a subsequent process will be used to identifying matching concepts.",
                      output_type=MentionList,
                      model_settings = ModelSettings(temperature=0.0))

    status_widget.update(label="Identifying mentions...")
    run_result_agent = sub_agent.run_sync("Please identify potential SNOMED concepts in the following text:\n\n" + text)
    mentions = run_result_agent.output.mentions
    usage = run_result_agent.usage()
    
    _log_mention_identification(extraction_logger, step_id, text, mentions, usage)
    
    mentions_str = set([mention.mention_str for mention in mentions])
    
    _log_deduplication(extraction_logger, len(mentions), mentions_str)

    coded_concepts: list[FullCodedConcept] = []
    for found_mention in mentions_str:
        status_widget.update(label=f"Coding '{found_mention}'...")
        coded_concept = code_mention(found_mention, text, status_widget, extraction_logger)
        coded_concepts.append(coded_concept)

    final_results = [concept.to_dict() for concept in coded_concepts]
    extraction_logger.finalize(final_results)
    
    return coded_concepts, extraction_logger


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


def get_hits_context(found_mention: str) -> ConceptCollection:
    """Get concept candidates for a mention from vector database.
    
    This is a pure utility function that performs vector search without logging.
    Logging should be handled at the caller level.
    """
    hits = vec_db.query(found_mention, 10) 
    concept_ids = [hit.concept_id for hit in hits]

    concept_collection = get_concept_ids_context(concept_ids)
    concept_collection.search_query = found_mention
    
    return concept_collection

def code_mention(found_mention: str, context: str, status_widget, extraction_logger: ExtractionLogger) -> FullCodedConcept:
    """Code a mention to an OMOP concept using AI agent with comprehensive logging.
    
    This function orchestrates the complete mention coding process:
    1. Initial vector search for concept candidates
    2. AI agent reasoning with optional tool usage:
       - Alternative vector search with expanded terminology
       - Hierarchical concept context exploration
    3. Standard concept mapping
    4. Final concept retrieval
    
    All steps are logged for transparency and debugging.
    
    Args:
        found_mention: The text mention to code (e.g., "NSTEMI", "diabetes")
        context: The surrounding text context for disambiguation
        status_widget: UI widget for status updates
        extraction_logger: Logger for capturing all process steps
        
    Returns:
        FullCodedConcept with complete OMOP metadata
    """
    mention_log = extraction_logger.start_mention_coding(found_mention)
    
    status_widget.update(label=f"Coding '{found_mention}'... querying databases...")

    step_id = extraction_logger.start_step("initial_vec_search", "initial_vector_search", f"Initial vector database search for '{found_mention}'")
    concept_collection = get_hits_context(found_mention)
    
    _log_initial_vector_search(extraction_logger, step_id, found_mention, concept_collection)

    sub_agent = Agent(DEFAULT_MODEL, 
                      system_prompt=f"You are a helpful assistant that identifies the best fitting OMOP concept from a list of candidates. The initial candidates were found using vector similarity search for '{found_mention}'. Given a context and a YAML-structured list of candidate OMOP concepts with hierarchical information, return the concept_id, concept_name, and whether it is negated in the context. If the initial vector search candidates are a poor fit (e.g., for acronyms or abbreviations), you can use the vector_search_alternative tool to search with expanded terminology. You can also explore the hierarchy using get_concept_context. Use the following examples and guidelines to guide your search: {examples}",
                      output_type=AgentCodedConcept,
                      model_settings = ModelSettings(temperature=0.0))

    @sub_agent.tool
    async def vector_search_alternative(ctx: RunContext, query: str) -> str:
        """Perform vector similarity search with alternative terminology. 
        
        Useful when the initial vector search results are poor (e.g., for acronyms like 'NSTEMI'). 
        Use expanded medical terminology (e.g., 'Non-ST elevation myocardial infarction' for 'NSTEMI').
        """
        status_widget.update(label=f"Coding '{found_mention}'... vector search with alternative terminology '{query}'...")
        
        step_id = extraction_logger.start_step("alt_vector_search", "alternative_vector_search", f"Vector search with alternative terminology")
        search_results = get_hits_context(query)
        
        _log_alternative_vector_search(extraction_logger, step_id, found_mention, query, search_results)
        
        return search_results.to_yaml()

    @sub_agent.tool
    async def get_concept_context(ctx: RunContext, concept_ids: list[str]) -> str:
        """Retrieve hierarchical context about concept IDs.
        
        Useful to identify potential more-general or more-specific concepts by exploring 
        parent and child relationships in the OMOP concept hierarchy.
        """
        status_widget.update(label=f"Coding '{found_mention}'... retrieving concept context...")
        
        step_id = extraction_logger.start_step("concept_context", "concept_context", "Retrieving hierarchical concept context")
        context_results = get_concept_ids_context(concept_ids)
        
        _log_concept_context_retrieval(extraction_logger, step_id, concept_ids, context_results)
        
        return context_results.to_yaml()

    step_id = extraction_logger.start_step("agent_reason", "agent_reasoning", "AI agent selecting best concept")
    
    yaml_candidates = concept_collection.to_yaml()
    instructions = f"From the following context, identify the best fitting OMOP concept and whether it is negated in the context:\n\nContext:\n```\n{context}\n```\n\nCandidate Concepts (YAML format):\n```yaml\n{yaml_candidates}\n```"

    run_result_agent = sub_agent.run_sync(instructions)
    run_result = run_result_agent.output
    coding_usage = run_result_agent.usage()
    
    _log_agent_reasoning(extraction_logger, step_id, concept_collection, context, run_result, coding_usage)
    
    original_concept_id = run_result.concept_id
    step_id = extraction_logger.start_step("mapping", "concept_mapping", "Checking for standard concept mapping")
    
    sql_query = f"SELECT concept_id_2 FROM concept_relationship WHERE concept_id_1 = {original_concept_id} AND relationship_id = 'Maps to'"
    query_result = sql_db.run_query(sql_query)
    
    if query_result:
        agent_picked_concept_id = query_result[0][0]
        status_widget.update(label=f"Coding '{found_mention}'... mapped to standard concept...")
        mapping_found = True
    else:
        agent_picked_concept_id = original_concept_id
        status_widget.update(label=f"Coding '{found_mention}'... using non-standard concept (no mapping available)...")
        mapping_found = False
    
    _log_concept_mapping(extraction_logger, step_id, original_concept_id, agent_picked_concept_id, mapping_found)

    step_id = extraction_logger.start_step("final_retrieval", "final_concept_retrieval", "Retrieving final concept details")
    
    sql_query = f"SELECT concept_id, concept_name, domain_id, vocabulary_id, concept_code, standard_concept FROM concept WHERE concept_id = {agent_picked_concept_id}"
    query_result = sql_db.run_query(sql_query)
    concept_data = query_result[0]
     
    coded_concept = FullCodedConcept(
         mention_str=found_mention,
         concept_id=str(concept_data[0]),
         concept_name=str(concept_data[1]),
         domain_id=str(concept_data[2]),
         vocabulary_id=str(concept_data[3]),
         concept_code=str(concept_data[4]),
         standard=concept_data[5] == 'S',
         negated=run_result.negated
     )
    
    _log_final_concept_retrieval(extraction_logger, step_id, agent_picked_concept_id, coded_concept)
    
    extraction_logger.finish_mention_coding(coded_concept.to_dict())

    return coded_concept


# ============================================================================
# LOGGING HELPER FUNCTIONS
# ============================================================================

def _log_mention_identification(extraction_logger: ExtractionLogger, step_id: str, text: str, mentions: list, usage) -> None:
    """Log mention identification results with usage statistics."""
    extraction_logger.log_step(
        step_type="mention_identification",
        description="Identified potential SNOMED mentions from text",
        input_data={"text_length": len(text), "model": DEFAULT_MODEL},
        output_data={
            "raw_mentions": [m.mention_str for m in mentions], 
            "total_mentions": len(mentions),
            "usage_stats": {
                "requests": usage.requests,
                "request_tokens": usage.request_tokens,
                "response_tokens": usage.response_tokens,
                "total_tokens": usage.total_tokens,
                "details": usage.details
            }
        },
        step_id=step_id
    )


def _log_deduplication(extraction_logger: ExtractionLogger, mentions_before: int, mentions_after: list) -> None:
    """Log mention deduplication results."""
    extraction_logger.log_step(
        step_type="deduplication",
        description="Removed duplicate mentions",
        input_data={"mentions_before": mentions_before},
        output_data={"mentions_after": len(mentions_after), "unique_mentions": list(mentions_after)}
    )


def _log_initial_vector_search(extraction_logger: ExtractionLogger, step_id: str, found_mention: str, concept_collection) -> None:
    """Log initial vector database search results."""
    concepts_data = [concept.to_dict() for concept in concept_collection.concepts]
    extraction_logger.log_step(
        step_type="initial_vector_search",
        description=f"Initial vector database search for '{found_mention}'",
        input_data={"query": found_mention, "max_results": 10},
        output_data={
            "concepts": concepts_data,
            "total_count": len(concept_collection.concepts),
            "search_query": found_mention
        },
        step_id=step_id
    )


def _log_alternative_vector_search(extraction_logger: ExtractionLogger, step_id: str, found_mention: str, query: str, search_results) -> None:
    """Log alternative vector search results."""
    concepts_data = [concept.to_dict() for concept in search_results.concepts]
    extraction_logger.log_step(
        step_type="alternative_vector_search",
        description=f"Vector search with alternative terminology '{query}'",
        input_data={"original_mention": found_mention, "alternative_query": query},
        output_data={
            "concepts": concepts_data,
            "total_count": search_results.total_count,
            "search_query": query
        },
        step_id=step_id
    )


def _log_concept_context_retrieval(extraction_logger: ExtractionLogger, step_id: str, concept_ids: list, context_results) -> None:
    """Log hierarchical concept context retrieval results."""
    concepts_data = [concept.to_dict() for concept in context_results.concepts]
    extraction_logger.log_step(
        step_type="concept_context",
        description=f"Retrieved hierarchical context for concept IDs",
        input_data={"concept_ids": concept_ids},
        output_data={
            "concepts": concepts_data,
            "total_count": len(context_results.concepts)
        },
        step_id=step_id
    )


def _log_agent_reasoning(extraction_logger: ExtractionLogger, step_id: str, concept_collection, context: str, run_result, coding_usage) -> None:
    """Log AI agent reasoning and concept selection results."""
    extraction_logger.log_step(
        step_type="agent_reasoning",
        description="AI agent selected best fitting concept",
        input_data={
            "model": DEFAULT_MODEL,
            "num_candidates": len(concept_collection.concepts),
            "context_length": len(context)
        },
        output_data={
            "selected_concept_id": run_result.concept_id,
            "selected_concept_name": run_result.concept_name,
            "negated": run_result.negated,
            "usage_stats": {
                "requests": coding_usage.requests,
                "request_tokens": coding_usage.request_tokens,
                "response_tokens": coding_usage.response_tokens,
                "total_tokens": coding_usage.total_tokens,
                "details": coding_usage.details
            }
        },
        step_id=step_id
    )


def _log_concept_mapping(extraction_logger: ExtractionLogger, step_id: str, original_concept_id: str, final_concept_id: str, mapping_found: bool) -> None:
    """Log standard concept mapping results."""
    extraction_logger.log_step(
        step_type="concept_mapping",
        description="Checked for standard concept mapping",
        input_data={"original_concept_id": original_concept_id},
        output_data={
            "final_concept_id": final_concept_id,
            "mapping_found": mapping_found
        },
        step_id=step_id
    )


def _log_final_concept_retrieval(extraction_logger: ExtractionLogger, step_id: str, concept_id: str, coded_concept) -> None:
    """Log final concept retrieval and details."""
    extraction_logger.log_step(
        step_type="final_concept_retrieval",
        description="Retrieved final concept details from database",
        input_data={"concept_id": concept_id},
        output_data=coded_concept.to_dict(),
        step_id=step_id
    )

