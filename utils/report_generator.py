"""Generate markdown reports from extraction logs."""

from typing import Dict, Any
from models.extraction_log import ExtractionProcessLog, LogStep, MentionCodingLog


def _format_duration(duration_ms: float) -> str:
    """Format duration in a human-readable way."""
    if duration_ms < 1000:
        return f"{duration_ms:.0f}ms"
    elif duration_ms < 60000:
        return f"{duration_ms/1000:.2f}s"
    else:
        minutes = duration_ms / 60000
        return f"{minutes:.2f}m"


def _format_step_data(data: Dict[str, Any], max_length: int = 200) -> str:
    """Format step data for display, truncating if needed."""
    if not data:
        return "None"
    
    # Convert to string representation
    if isinstance(data, dict):
        # For dictionaries, show key-value pairs concisely
        items = []
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            items.append(f"{key}: {value}")
        result = "{" + ", ".join(items) + "}"
    else:
        result = str(data)
    
    # Truncate if too long
    if len(result) > max_length:
        result = result[:max_length-3] + "..."
    
    return result


def _format_concept_list(concepts: list, max_display: int = 20) -> str:
    """Format a list of concepts for detailed display."""
    if not concepts:
        return "None found"
    
    lines = []
    for i, concept in enumerate(concepts[:max_display]):
        if isinstance(concept, dict):
            concept_id = concept.get('concept_id', 'Unknown')
            concept_name = concept.get('concept_name', 'Unknown')
            domain = concept.get('domain_id', 'Unknown')
            standard = concept.get('standard', False)
            standard_marker = " [STANDARD]" if standard else " [NON-STANDARD]"
            lines.append(f"  {i+1}. {concept_name} (ID: {concept_id}, Domain: {domain}){standard_marker}")
        else:
            lines.append(f"  {i+1}. {concept}")
    
    if len(concepts) > max_display:
        lines.append(f"  ... and {len(concepts) - max_display} more concepts")
    
    return "\n".join(lines)


def _format_search_results(output_data: Dict[str, Any]) -> str:
    """Format search results with detailed concept information."""
    if not output_data:
        return "No data available"
    
    lines = []
    
    # Add basic search info
    if 'search_query' in output_data:
        lines.append(f"**Search Query**: {output_data['search_query']}")
    if 'total_count' in output_data:
        lines.append(f"**Results Found**: {output_data['total_count']}")
    
    # Add concept details if available
    if 'concepts' in output_data and output_data['concepts']:
        lines.append("**Concept Candidates**:")
        lines.append(_format_concept_list(output_data['concepts']))
    elif 'concept_ids' in output_data:
        lines.append(f"**Concept IDs Retrieved**: {', '.join(map(str, output_data['concept_ids']))}")
    
    return "\n".join(lines) if lines else "No detailed results available"


def _generate_detailed_step_info(step: LogStep) -> str:
    """Generate detailed information for a step."""
    lines = []
    
    # Input data
    if step.input_data:
        lines.append("\n**Input Data:**")
        if step.step_type in ['initial_vector_search', 'vector_search', 'string_search', 'alternative_vector_search']:
            if 'query' in step.input_data:
                lines.append(f"- Query: '{step.input_data['query']}'")
            if 'alternative_query' in step.input_data:
                lines.append(f"- Alternative Query: '{step.input_data['alternative_query']}'")
            if 'max_results' in step.input_data:
                lines.append(f"- Max Results: {step.input_data['max_results']}")
            if 'original_mention' in step.input_data:
                lines.append(f"- Original Mention: '{step.input_data['original_mention']}'")
        elif step.step_type == 'concept_context':
            if 'concept_ids' in step.input_data:
                concept_ids = step.input_data['concept_ids']
                lines.append(f"- Concept IDs: {', '.join(map(str, concept_ids))}")
        elif step.step_type == 'agent_reasoning':
            if 'num_candidates' in step.input_data:
                lines.append(f"- Candidate Concepts: {step.input_data['num_candidates']}")
            if 'context_length' in step.input_data:
                lines.append(f"- Context Length: {step.input_data['context_length']} characters")
            if 'model' in step.input_data:
                lines.append(f"- Model: {step.input_data['model']}")
        else:
            # Generic formatting for other step types
            for key, value in step.input_data.items():
                if isinstance(value, (list, dict)) and len(str(value)) > 100:
                    lines.append(f"- {key}: [Complex data structure with {len(value) if hasattr(value, '__len__') else 'multiple'} items]")
                else:
                    lines.append(f"- {key}: {value}")
    
    # Output data with special formatting
    if step.output_data:
        lines.append("\n**Output Data:**")
        if step.step_type in ['initial_vector_search', 'vector_search', 'string_search', 'alternative_vector_search']:
            search_result = _format_search_results(step.output_data)
            # Add proper indentation for search results
            for line in search_result.split('\n'):
                if line.strip():
                    if line.startswith('**'):
                        lines.append(f"- {line}")
                    else:
                        lines.append(line)
        elif step.step_type == 'agent_reasoning':
            if 'selected_concept_id' in step.output_data:
                lines.append(f"- Selected Concept: {step.output_data.get('selected_concept_name', 'Unknown')} (ID: {step.output_data['selected_concept_id']})")
            if 'negated' in step.output_data:
                lines.append(f"- Negated: {step.output_data['negated']}")
            # Add usage stats for agent reasoning
            if 'usage_stats' in step.output_data:
                usage = step.output_data['usage_stats']
                lines.append(f"- Token Usage: {usage.get('total_tokens', 0)} tokens ({usage.get('request_tokens', 0)} request + {usage.get('response_tokens', 0)} response)")
        elif step.step_type == 'concept_mapping':
            if 'mapping_found' in step.output_data:
                lines.append(f"- Standard Mapping Found: {step.output_data['mapping_found']}")
            if 'original_concept_id' in step.output_data and 'final_concept_id' in step.output_data:
                orig = step.output_data['original_concept_id']
                final = step.output_data['final_concept_id']
                if orig != final:
                    lines.append(f"- Mapped from {orig} to {final}")
                else:
                    lines.append(f"- Used original concept {orig} (no mapping available)")
        elif step.step_type == 'final_concept_retrieval':
            if 'concept_name' in step.output_data:
                lines.append(f"- Final Concept: {step.output_data.get('concept_name')} (ID: {step.output_data.get('concept_id')})")
            if 'domain_id' in step.output_data:
                lines.append(f"- Domain: {step.output_data.get('domain_id')}")
            if 'standard' in step.output_data:
                standard_status = "STANDARD" if step.output_data['standard'] else "NON-STANDARD"
                lines.append(f"- Standard Status: {standard_status}")
        else:
            # Generic output formatting
            for key, value in step.output_data.items():
                if key == 'usage_stats' and isinstance(value, dict):
                    # Format usage statistics nicely
                    lines.append(f"- Token Usage: {value.get('total_tokens', 0)} tokens ({value.get('request_tokens', 0)} request + {value.get('response_tokens', 0)} response)")
                elif isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and 'concept_name' in value[0]:
                        # This looks like a concept list
                        lines.append(f"- {key}:")
                        concept_list = _format_concept_list(value)
                        for line in concept_list.split('\n'):
                            if line.strip():
                                lines.append(f"  {line}")  # Add extra indentation for concept lists
                    elif len(str(value)) > 100:
                        lines.append(f"- {key}: [List with {len(value)} items]")
                    else:
                        lines.append(f"- {key}: {value}")
                elif isinstance(value, dict) and len(str(value)) > 100:
                    lines.append(f"- {key}: [Complex data structure]")
                else:
                    lines.append(f"- {key}: {value}")
    
    return "\n".join(lines) if lines else ""


def _generate_step_summary(step: LogStep) -> str:
    """Generate a summary line for a step."""
    duration_str = f" ({_format_duration(step.duration_ms)})" if step.duration_ms else ""
    error_str = f" ERROR: {step.error}" if step.error else ""
    return f"- **{step.step_type}**: {step.description}{duration_str}{error_str}"


def _generate_mention_section(mention_log: MentionCodingLog) -> str:
    """Generate markdown section for a mention's coding process."""
    mention = mention_log.mention
    steps = mention_log.steps
    final_result = mention_log.final_result
    
    # Calculate total duration for this mention
    total_duration = sum(step.duration_ms for step in steps if step.duration_ms)
    duration_str = f" ({_format_duration(total_duration)})" if total_duration > 0 else ""
    
    sections = [f"### Coding: '{mention}'{duration_str}", ""]
    
    if final_result:
        concept_name = final_result.get('concept_name', 'Unknown')
        concept_id = final_result.get('concept_id', 'Unknown')
        domain = final_result.get('domain_id', 'Unknown')
        standard = final_result.get('standard', False)
        negated = final_result.get('negated', False)
        
        standard_str = " [STANDARD]" if standard else " [NON-STANDARD]"
        negated_str = " (negated)" if negated else ""
        sections.append(f"**Final Result**: {concept_name} (ID: {concept_id}, Domain: {domain}){standard_str}{negated_str}")
        sections.append("")
    
    if steps:
        sections.append("**Processing Steps:**")
        sections.append("")
        for i, step in enumerate(steps, 1):
            sections.append(f"#### Step {i}: {step.step_type}")
            sections.append(_generate_step_summary(step))
            
            # Add detailed step information
            detailed_info = _generate_detailed_step_info(step)
            if detailed_info:
                sections.append(detailed_info)
            sections.append("")
    
    return "\n".join(sections)


def generate_markdown_report(log: ExtractionProcessLog) -> str:
    """Generate a comprehensive markdown report from an extraction log."""
    
    # Header and summary
    total_duration = log.get_total_duration_ms()
    duration_str = f" ({_format_duration(total_duration)})" if total_duration else ""
    
    report = [
        f"# Extraction Process Report{duration_str}",
        f"**Process ID**: `{log.process_id}`",
        f"**Start Time**: {log.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**End Time**: {log.end_time.strftime('%Y-%m-%d %H:%M:%S') if log.end_time else 'In Progress'}",
        f"**Text Length**: {len(log.input_text)} characters",
        ""
    ]
    
    # Input text first
    report.extend([
        "## Input Text",
        ""
    ])
    
    if len(log.input_text) > 2000:
        truncated_text = log.input_text[:2000] + "..."
        report.append(f"```\n{truncated_text}\n```")
        report.append(f"*(Text truncated - showing first 2000 of {len(log.input_text)} characters)*")
    else:
        report.append(f"```\n{log.input_text}\n```")
    
    report.append("")
    
    # Summary statistics with better metrics
    num_mentions = len(log.mention_logs)
    num_final_results = len(log.final_results)
    num_standard = sum(1 for result in log.final_results if result.get('standard', False))
    num_negated = sum(1 for result in log.final_results if result.get('negated', False))
    
    # Get usage statistics
    usage_stats = log.get_usage_statistics()
    
    report.extend([
        "## Process Summary",
        f"- **Mentions identified**: {num_mentions}",
        f"- **Concepts coded**: {num_final_results}",
        f"- **Standard concepts found**: {num_standard}",
        f"- **Negated concepts**: {num_negated}",
        f"- **Total processing time**: {_format_duration(total_duration)}" if total_duration else "- **Total processing time**: Unknown",
        ""
    ])
    
    # Add usage statistics section
    if usage_stats['total_requests'] > 0:
        from models.model_config import format_cost
        
        report.extend([
            "## Token Usage & Cost Statistics",
            f"- **Total API Requests**: {usage_stats['total_requests']}",
            f"- **Request Tokens**: {usage_stats['total_request_tokens']:,}",
            f"- **Response Tokens**: {usage_stats['total_response_tokens']:,}",
            f"- **Total Tokens**: {usage_stats['total_tokens']:,}",
            f"- **Total Cost**: {format_cost(usage_stats['total_cost'])}",
            f"- **Average Tokens per Request**: {usage_stats['avg_tokens_per_request']:.1f}",
            f"- **Average Cost per Request**: {format_cost(usage_stats['avg_cost_per_request'])}",
            ""
        ])
        
        # Show models used
        if usage_stats['models_used']:
            models_list = ', '.join(usage_stats['models_used'])
            report.extend([
                f"- **Models Used**: {models_list}",
                ""
            ])
        
        # Add detailed breakdown if any non-zero values exist
        details = usage_stats['details']
        if any(details.values()):
            report.extend([
                "### Detailed Token Breakdown",
                f"- **Cached Tokens**: {details['cached_tokens']:,}",
                f"- **Reasoning Tokens**: {details['reasoning_tokens']:,}",
                f"- **Accepted Prediction Tokens**: {details['accepted_prediction_tokens']:,}",
                f"- **Rejected Prediction Tokens**: {details['rejected_prediction_tokens']:,}",
                f"- **Audio Tokens**: {details['audio_tokens']:,}",
                ""
            ])
    
    # Top-level process steps with details
    if log.steps:
        report.extend([
            "## Process Overview",
            ""
        ])
        for i, step in enumerate(log.steps, 1):
            report.append(f"### Step {i}: {step.step_type}")
            report.append(_generate_step_summary(step))
            detailed_info = _generate_detailed_step_info(step)
            if detailed_info:
                report.append(detailed_info)
            report.append("")
    
    # Individual mention coding with full details
    if log.mention_logs:
        report.extend([
            "## Detailed Mention Coding Process",
            ""
        ])
        
        for mention_log in log.mention_logs:
            report.append(_generate_mention_section(mention_log))
            report.append("")
    
    # Final results summary with complete information
    if log.final_results:
        report.extend([
            "## Final Results Summary",
            ""
        ])
        
        for i, result in enumerate(log.final_results, 1):
            mention = result.get('mention_str', 'Unknown')
            concept_name = result.get('concept_name', 'Unknown')
            concept_id = result.get('concept_id', 'Unknown')
            domain = result.get('domain_id', 'Unknown')
            vocabulary = result.get('vocabulary_id', 'Unknown')
            concept_code = result.get('concept_code', 'Unknown')
            negated = result.get('negated', False)
            standard = result.get('standard', False)
            
            negated_str = " (negated)" if negated else ""
            standard_str = " [STANDARD]" if standard else " [NON-STANDARD]"
            
            report.append(f"{i}. **'{mention}'** → {concept_name}")
            report.append(f"   - **Concept ID**: {concept_id}")
            report.append(f"   - **Domain**: {domain}")
            report.append(f"   - **Vocabulary**: {vocabulary}")
            report.append(f"   - **Concept Code**: {concept_code}")
            report.append(f"   - **Standard Status**: {standard_str.strip()}")
            if negated:
                report.append(f"   - **Negated**: Yes")
            report.append("")
    
    return "\n".join(report)


def generate_summary_stats(log: ExtractionProcessLog) -> Dict[str, Any]:
    """Generate summary statistics from the log."""
    total_duration = log.get_total_duration_ms()
    num_mentions = len(log.mention_logs)
    num_results = len(log.final_results)
    
    # Count different types of steps
    step_counts = {}
    for mention_log in log.mention_logs:
        for step in mention_log.steps:
            step_counts[step.step_type] = step_counts.get(step.step_type, 0) + 1
    
    # Average time per mention
    avg_time_per_mention = None
    if num_mentions > 0 and total_duration:
        avg_time_per_mention = total_duration / num_mentions
    
    return {
        "total_duration_ms": total_duration,
        "num_mentions_identified": num_mentions,
        "num_concepts_coded": num_results,
        "success_rate": (num_results / num_mentions * 100) if num_mentions > 0 else 0,
        "avg_time_per_mention_ms": avg_time_per_mention,
        "step_type_counts": step_counts,
        "text_length": len(log.input_text)
    }
