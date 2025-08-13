from pydantic import Field
from pydantic.dataclasses import dataclass
from pydantic_ai import Agent
from ui.utils import OMOP_DOMAINS, OMOP_DOMAINS_LITERAL


# I believe that pydantic_ai uses type information to build the function-calling schema to support
# structured output, so we use dataclass and Field and the Literal type to define the expected output format.
@dataclass
class SearchConcept:
    concept_string: str = Field(..., description="The string containing a potential SNOMED concept or synonym to identify.")
    negated: bool = Field(False, description="Whether the concept is negated in the input text.")
    probable_domain: OMOP_DOMAINS_LITERAL = Field(..., description=f"The domain that the concept is most likely to belong to. One of {', '.join(OMOP_DOMAINS)}.")

@dataclass
class SearchConceptList:
    concepts: list[SearchConcept] = Field(..., description="A list of SNOMED concepts identified in the input text.")


def extract_concepts(text: str) -> SearchConceptList:
    """Given an input text, returns a list of strings representing potnentially codable SNOMED concepts or synonyms to identify. Entries can be negated to indicate the concept was mentioned in a negated context."""

    sub_agent = Agent("gpt-4.1", 
                      system_prompt="You are a helpful assistant that extracts potential SNOMED concepts or synonyms from clinical text. For each concept, determine if it is negated in the context. Return the results as a SearchConceptList dataclass.",
                      output_type=SearchConceptList)

    run_result = sub_agent.run_sync("Please identify potential SNOMED concepts in the following text:\n\n" + text)
    
    return run_result.output
