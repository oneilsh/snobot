"""
Enhanced Span Analysis Tool for SNOMED Entity Linking Evaluation

This module provides detailed analysis of span overlaps between agent predictions
and gold standard annotations, helping diagnose where the agent is performing
well and where it needs improvement.
"""

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from collections import defaultdict
import re


class OverlapType(Enum):
    """Types of overlap between predicted and gold standard spans"""
    EXACT_MATCH = "exact_match"           # Perfect match (same start, end, concept)
    PARTIAL_OVERLAP = "partial_overlap"   # Spans overlap but not exactly
    CONCEPT_MISMATCH = "concept_mismatch" # Same span, wrong concept
    NO_OVERLAP = "no_overlap"            # No overlap between spans


@dataclass
class SpanInfo:
    """Information about a single span"""
    note_id: str
    start: int
    end: int
    text: str
    concept_id: int
    concept_name: str = ""
    source: str = ""  # "agent" or "gold"
    
    def __post_init__(self):
        # Ensure concept_id is int
        self.concept_id = int(self.concept_id)
    
    @property
    def length(self) -> int:
        return self.end - self.start
    
    def overlaps_with(self, other: 'SpanInfo') -> bool:
        """Check if this span overlaps with another span"""
        return not (self.end <= other.start or other.end <= self.start)
    
    def overlap_length(self, other: 'SpanInfo') -> int:
        """Calculate the length of overlap with another span"""
        if not self.overlaps_with(other):
            return 0
        return min(self.end, other.end) - max(self.start, other.start)
    
    def iou_with(self, other: 'SpanInfo') -> float:
        """Calculate IoU (Intersection over Union) with another span"""
        intersection = self.overlap_length(other)
        if intersection == 0:
            return 0.0
        union = self.length + other.length - intersection
        return intersection / union if union > 0 else 0.0


@dataclass
class SpanComparison:
    """Detailed comparison between agent and gold standard spans"""
    agent_span: Optional[SpanInfo]
    gold_span: Optional[SpanInfo]
    overlap_type: OverlapType
    iou_score: float
    overlap_length: int
    notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "agent_span": asdict(self.agent_span) if self.agent_span else None,
            "gold_span": asdict(self.gold_span) if self.gold_span else None,
            "overlap_type": self.overlap_type.value,
            "iou_score": round(self.iou_score, 4),
            "overlap_length": self.overlap_length,
            "notes": self.notes
        }


class SpanAnalyzer:
    """Comprehensive span analysis for SNOMED entity linking evaluation"""
    
    def __init__(self, sql_db=None):
        """Initialize the analyzer with optional SQL database for concept lookups"""
        self.sql_db = sql_db
        self.concept_name_cache = {}
    
    def get_concept_name(self, concept_id: int) -> str:
        """Get concept name from concept_id (SNOMED code), with caching"""
        if concept_id in self.concept_name_cache:
            return self.concept_name_cache[concept_id]
        
        if self.sql_db:
            try:
                # Try looking up by concept_code first (for SNOMED codes)
                query = f"SELECT concept_name FROM concept WHERE concept_code = '{concept_id}' AND vocabulary_id IN ('SNOMED', 'SNOMEDCT_US')"
                result = self.sql_db.run_query(query)
                if result and len(result) > 0:
                    name = str(result[0][0])
                    self.concept_name_cache[concept_id] = name
                    return name
                
                # Fallback to concept_id lookup (for OMOP concept IDs)
                query = f"SELECT concept_name FROM concept WHERE concept_id = {concept_id}"
                result = self.sql_db.run_query(query)
                if result and len(result) > 0:
                    name = str(result[0][0])
                    self.concept_name_cache[concept_id] = name
                    return name
                    
            except Exception as e:
                logging.warning(f"Could not fetch concept name for {concept_id}: {e}")
        
        self.concept_name_cache[concept_id] = f"Unknown concept {concept_id}"
        return self.concept_name_cache[concept_id]
    
    def load_spans_from_csv(self, csv_path: str, source: str, text_data: Dict[str, str] = None) -> List[SpanInfo]:
        """Load spans from CSV file (either agent predictions or gold standard)"""
        df = pd.read_csv(csv_path)
        spans = []
        
        for _, row in df.iterrows():
            # Extract text from the span if text_data is provided
            text = ""
            if text_data and row['note_id'] in text_data:
                full_text = text_data[row['note_id']]
                text = full_text[row['start']:row['end']]
            
            # Get concept name
            concept_name = self.get_concept_name(row['concept_id'])
            
            span = SpanInfo(
                note_id=str(row['note_id']),
                start=int(row['start']),
                end=int(row['end']),
                text=text,
                concept_id=int(row['concept_id']),
                concept_name=concept_name,
                source=source
            )
            spans.append(span)
        
        return spans
    
    def load_text_data(self, notes_csv_path: str) -> Dict[str, str]:
        """Load text data from notes CSV file"""
        df = pd.read_csv(notes_csv_path)
        text_data = {}
        for _, row in df.iterrows():
            text_data[str(row['note_id'])] = str(row['text'])
        return text_data
    
    def analyze_spans(self, agent_spans: List[SpanInfo], gold_spans: List[SpanInfo], 
                     iou_threshold: float = 0.5) -> Dict[str, Any]:
        """
        Comprehensive analysis of spans comparing agent predictions to gold standard
        
        Args:
            agent_spans: List of agent-predicted spans
            gold_spans: List of gold standard spans  
            iou_threshold: Minimum IoU for considering spans as matching
            
        Returns:
            Detailed analysis results
        """
        # Group spans by note_id
        agent_by_note = defaultdict(list)
        gold_by_note = defaultdict(list)
        
        for span in agent_spans:
            agent_by_note[span.note_id].append(span)
        
        for span in gold_spans:
            gold_by_note[span.note_id].append(span)
        
        # Get all note_ids
        all_notes = set(agent_by_note.keys()) | set(gold_by_note.keys())
        
        # Perform detailed analysis
        comparisons = []
        stats = {
            "total_agent_spans": len(agent_spans),
            "total_gold_spans": len(gold_spans),
            "notes_processed": len(all_notes),
            "exact_matches": 0,
            "partial_overlaps": 0,
            "concept_mismatches": 0,
            "agent_only_spans": 0,
            "gold_only_spans": 0,
            "by_concept_id": defaultdict(lambda: {
                "agent_count": 0, "gold_count": 0, "matches": 0, "concept_name": ""
            }),
            "by_note_id": {}
        }
        
        for note_id in all_notes:
            note_agent_spans = agent_by_note.get(note_id, [])
            note_gold_spans = gold_by_note.get(note_id, [])
            
            note_stats = self._analyze_note_spans(
                note_agent_spans, note_gold_spans, iou_threshold
            )
            
            stats["by_note_id"][note_id] = note_stats
            # Convert comparison dicts back to objects for processing
            note_comparisons = []
            for comp_dict in note_stats["comparisons"]:
                # Reconstruct SpanComparison objects from dict for further processing
                agent_span = SpanInfo(**comp_dict["agent_span"]) if comp_dict["agent_span"] else None
                gold_span = SpanInfo(**comp_dict["gold_span"]) if comp_dict["gold_span"] else None
                overlap_type = OverlapType(comp_dict["overlap_type"])
                comparison = SpanComparison(
                    agent_span=agent_span,
                    gold_span=gold_span,
                    overlap_type=overlap_type,
                    iou_score=comp_dict["iou_score"],
                    overlap_length=comp_dict["overlap_length"],
                    notes=comp_dict["notes"]
                )
                note_comparisons.append(comparison)
            comparisons.extend(note_comparisons)
            
            # Aggregate stats
            stats["exact_matches"] += note_stats["exact_matches"]
            stats["partial_overlaps"] += note_stats["partial_overlaps"]
            stats["concept_mismatches"] += note_stats["concept_mismatches"]
            stats["agent_only_spans"] += note_stats["agent_only_spans"]
            stats["gold_only_spans"] += note_stats["gold_only_spans"]
        
        # Aggregate concept-level statistics
        for span in agent_spans:
            stats["by_concept_id"][span.concept_id]["agent_count"] += 1
            stats["by_concept_id"][span.concept_id]["concept_name"] = span.concept_name
        
        for span in gold_spans:
            stats["by_concept_id"][span.concept_id]["gold_count"] += 1
            stats["by_concept_id"][span.concept_id]["concept_name"] = span.concept_name
        
        for comparison in comparisons:
            if comparison.overlap_type == OverlapType.EXACT_MATCH:
                concept_id = comparison.agent_span.concept_id
                stats["by_concept_id"][concept_id]["matches"] += 1
        
        # Convert defaultdict to regular dict for JSON serialization
        stats["by_concept_id"] = dict(stats["by_concept_id"])
        
        return {
            "statistics": stats,
            "comparisons": comparisons,
            "analysis_parameters": {
                "iou_threshold": iou_threshold
            }
        }
    
    def _analyze_note_spans(self, agent_spans: List[SpanInfo], gold_spans: List[SpanInfo],
                           iou_threshold: float) -> Dict[str, Any]:
        """Analyze spans for a single note"""
        comparisons = []
        matched_agent_indices = set()
        matched_gold_indices = set()
        
        stats = {
            "agent_span_count": len(agent_spans),
            "gold_span_count": len(gold_spans),
            "exact_matches": 0,
            "partial_overlaps": 0,
            "concept_mismatches": 0,
            "agent_only_spans": 0,
            "gold_only_spans": 0,
            "comparisons": []
        }
        
        # Find best matches for each agent span
        for i, agent_span in enumerate(agent_spans):
            best_match = None
            best_iou = 0.0
            best_gold_idx = -1
            
            for j, gold_span in enumerate(gold_spans):
                if j in matched_gold_indices:
                    continue
                
                iou = agent_span.iou_with(gold_span)
                if iou > best_iou and iou >= iou_threshold:
                    best_iou = iou
                    best_match = gold_span
                    best_gold_idx = j
            
            if best_match:
                # Found a match
                matched_agent_indices.add(i)
                matched_gold_indices.add(best_gold_idx)
                
                # Determine overlap type
                if (agent_span.start == best_match.start and 
                    agent_span.end == best_match.end and
                    agent_span.concept_id == best_match.concept_id):
                    overlap_type = OverlapType.EXACT_MATCH
                    stats["exact_matches"] += 1
                elif agent_span.concept_id != best_match.concept_id:
                    overlap_type = OverlapType.CONCEPT_MISMATCH
                    stats["concept_mismatches"] += 1
                else:
                    overlap_type = OverlapType.PARTIAL_OVERLAP
                    stats["partial_overlaps"] += 1
                
                comparison = SpanComparison(
                    agent_span=agent_span,
                    gold_span=best_match,
                    overlap_type=overlap_type,
                    iou_score=best_iou,
                    overlap_length=agent_span.overlap_length(best_match),
                    notes=self._generate_comparison_notes(agent_span, best_match, overlap_type)
                )
                comparisons.append(comparison)
        
        # Handle unmatched agent spans
        for i, agent_span in enumerate(agent_spans):
            if i not in matched_agent_indices:
                stats["agent_only_spans"] += 1
                comparison = SpanComparison(
                    agent_span=agent_span,
                    gold_span=None,
                    overlap_type=OverlapType.NO_OVERLAP,
                    iou_score=0.0,
                    overlap_length=0,
                    notes=["Agent predicted this span but no corresponding gold standard span found"]
                )
                comparisons.append(comparison)
        
        # Handle unmatched gold spans
        for j, gold_span in enumerate(gold_spans):
            if j not in matched_gold_indices:
                stats["gold_only_spans"] += 1
                comparison = SpanComparison(
                    agent_span=None,
                    gold_span=gold_span,
                    overlap_type=OverlapType.NO_OVERLAP,
                    iou_score=0.0,
                    overlap_length=0,
                    notes=["Gold standard span that agent failed to predict"]
                )
                comparisons.append(comparison)
        
        stats["comparisons"] = [comp.to_dict() for comp in comparisons]
        return stats
    
    def _generate_comparison_notes(self, agent_span: SpanInfo, gold_span: SpanInfo, 
                                 overlap_type: OverlapType) -> List[str]:
        """Generate descriptive notes about the comparison"""
        notes = []
        
        if overlap_type == OverlapType.EXACT_MATCH:
            notes.append("Perfect match: same span boundaries and concept")
        elif overlap_type == OverlapType.CONCEPT_MISMATCH:
            notes.append(f"Span boundaries match but concept differs: agent={agent_span.concept_name} vs gold={gold_span.concept_name}")
        elif overlap_type == OverlapType.PARTIAL_OVERLAP:
            notes.append(f"Partial overlap: agent=({agent_span.start}-{agent_span.end}) vs gold=({gold_span.start}-{gold_span.end})")
            if agent_span.text != gold_span.text:
                notes.append(f"Text differs: agent='{agent_span.text}' vs gold='{gold_span.text}'")
        
        return notes
    
    def generate_enhanced_summary(self, analysis_results: Dict[str, Any], 
                                output_path: str) -> str:
        """Generate an enhanced summary report with detailed span analysis"""
        
        stats = analysis_results["statistics"]
        comparisons = analysis_results["comparisons"]
        
        # Create summary structure
        summary = {
            "span_analysis_summary": {
                "total_spans": {
                    "agent_predictions": stats["total_agent_spans"],
                    "gold_standard": stats["total_gold_spans"],
                    "notes_processed": stats["notes_processed"]
                },
                "overlap_analysis": {
                    "exact_matches": stats["exact_matches"],
                    "partial_overlaps": stats["partial_overlaps"], 
                    "concept_mismatches": stats["concept_mismatches"],
                    "agent_only_spans": stats["agent_only_spans"],
                    "gold_only_spans": stats["gold_only_spans"]
                },
                "performance_metrics": {
                    "precision": stats["exact_matches"] / stats["total_agent_spans"] if stats["total_agent_spans"] > 0 else 0,
                    "recall": stats["exact_matches"] / stats["total_gold_spans"] if stats["total_gold_spans"] > 0 else 0,
                    "match_rate": stats["exact_matches"] / max(stats["total_agent_spans"], stats["total_gold_spans"]) if max(stats["total_agent_spans"], stats["total_gold_spans"]) > 0 else 0
                }
            },
            "concept_level_analysis": {},
            "note_level_analysis": {},
            "detailed_comparisons": {
                "exact_matches": [],
                "partial_overlaps": [],
                "concept_mismatches": [],
                "agent_only_spans": [],
                "gold_only_spans": []
            }
        }
        
        # Add concept-level analysis
        for concept_id, concept_stats in stats["by_concept_id"].items():
            summary["concept_level_analysis"][str(concept_id)] = {
                "concept_name": concept_stats["concept_name"],
                "agent_predictions": concept_stats["agent_count"],
                "gold_standard_count": concept_stats["gold_count"],
                "exact_matches": concept_stats["matches"],
                "precision": concept_stats["matches"] / concept_stats["agent_count"] if concept_stats["agent_count"] > 0 else 0,
                "recall": concept_stats["matches"] / concept_stats["gold_count"] if concept_stats["gold_count"] > 0 else 0
            }
        
        # Add note-level analysis
        summary["note_level_analysis"] = stats["by_note_id"]
        
        # Organize detailed comparisons by type
        for comparison in comparisons:
            comp_dict = comparison.to_dict()
            overlap_type = comparison.overlap_type.value
            
            if overlap_type == "exact_match":
                summary["detailed_comparisons"]["exact_matches"].append(comp_dict)
            elif overlap_type == "partial_overlap":
                summary["detailed_comparisons"]["partial_overlaps"].append(comp_dict)
            elif overlap_type == "concept_mismatch":
                summary["detailed_comparisons"]["concept_mismatches"].append(comp_dict)
            elif overlap_type == "no_overlap":
                if comp_dict["agent_span"] and not comp_dict["gold_span"]:
                    summary["detailed_comparisons"]["agent_only_spans"].append(comp_dict)
                elif comp_dict["gold_span"] and not comp_dict["agent_span"]:
                    summary["detailed_comparisons"]["gold_only_spans"].append(comp_dict)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Enhanced span analysis summary saved to {output_path}")
        return output_path
    
    def create_span_visualization(self, analysis_results: Dict[str, Any], 
                                note_id: str, output_path: str, note_text: str = None) -> str:
        """Create a markdown visualization of span overlaps for a specific note"""
        
        note_stats = analysis_results["statistics"]["by_note_id"].get(note_id)
        if not note_stats:
            raise ValueError(f"No analysis data found for note_id: {note_id}")
        
        # Convert dict comparisons back to SpanComparison objects for visualization
        comparisons = []
        for comp_dict in note_stats["comparisons"]:
            agent_span = SpanInfo(**comp_dict["agent_span"]) if comp_dict["agent_span"] else None
            gold_span = SpanInfo(**comp_dict["gold_span"]) if comp_dict["gold_span"] else None
            overlap_type = OverlapType(comp_dict["overlap_type"])
            comparison = SpanComparison(
                agent_span=agent_span,
                gold_span=gold_span,
                overlap_type=overlap_type,
                iou_score=comp_dict["iou_score"],
                overlap_length=comp_dict["overlap_length"],
                notes=comp_dict["notes"]
            )
            comparisons.append(comparison)
        
        # Create markdown visualization
        lines = [
            f"# Span Analysis for Note: {note_id}",
            "",
            "## Summary Statistics",
            "",
            f"- **Agent Spans:** {note_stats['agent_span_count']}",
            f"- **Gold Standard Spans:** {note_stats['gold_span_count']}",
            f"- **Exact Matches:** {note_stats['exact_matches']}",
            f"- **Partial Overlaps:** {note_stats['partial_overlaps']}",
            f"- **Concept Mismatches:** {note_stats['concept_mismatches']}",
            f"- **Agent Only (False Positives):** {note_stats['agent_only_spans']}",
            f"- **Gold Only (Missed):** {note_stats['gold_only_spans']}",
            "",
            "## Detailed Span Comparisons",
            ""
        ]
        
        # Group comparisons by type for better organization
        comparison_groups = {
            "Exact Matches": [],
            "Partial Overlaps": [],
            "Concept Mismatches": [],
            "Agent Only": [],
            "Gold Only": []
        }
        
        for comp in comparisons:
            if comp.overlap_type == OverlapType.EXACT_MATCH:
                comparison_groups["Exact Matches"].append(comp)
            elif comp.overlap_type == OverlapType.PARTIAL_OVERLAP:
                comparison_groups["Partial Overlaps"].append(comp)
            elif comp.overlap_type == OverlapType.CONCEPT_MISMATCH:
                comparison_groups["Concept Mismatches"].append(comp)
            elif comp.overlap_type == OverlapType.NO_OVERLAP:
                if comp.agent_span and not comp.gold_span:
                    comparison_groups["Agent Only"].append(comp)
                elif comp.gold_span and not comp.agent_span:
                    comparison_groups["Gold Only"].append(comp)
        
        for group_name, group_comparisons in comparison_groups.items():
            if group_comparisons:
                lines.extend([f"### {group_name}", ""])
                
                for comp in group_comparisons:
                    if comp.agent_span and comp.gold_span:
                        lines.extend([
                            f"**Agent:** `[{comp.agent_span.start}-{comp.agent_span.end}]` *\"{comp.agent_span.text}\"* → **{comp.agent_span.concept_name}** (`{comp.agent_span.concept_id}`)",
                            f"**Gold:**  `[{comp.gold_span.start}-{comp.gold_span.end}]` *\"{comp.gold_span.text}\"* → **{comp.gold_span.concept_name}** (`{comp.gold_span.concept_id}`)",
                            f"**IoU:** {comp.iou_score:.3f}, **Overlap:** {comp.overlap_length} chars",
                            ""
                        ])
                    elif comp.agent_span:
                        lines.extend([
                            f"**Agent:** `[{comp.agent_span.start}-{comp.agent_span.end}]` *\"{comp.agent_span.text}\"* → **{comp.agent_span.concept_name}** (`{comp.agent_span.concept_id}`)",
                            f"*(No corresponding gold standard span)*",
                            ""
                        ])
                    elif comp.gold_span:
                        lines.extend([
                            f"**Gold:**  `[{comp.gold_span.start}-{comp.gold_span.end}]` *\"{comp.gold_span.text}\"* → **{comp.gold_span.concept_name}** (`{comp.gold_span.concept_id}`)",
                            f"*(Missed by agent)*",
                            ""
                        ])
        
        # Add original text section if provided
        if note_text:
            lines.extend([
                "## Original Note Text",
                "",
                "```",
                note_text,
                "```",
                "",
                "---",
                "",
                "### Character Position Reference",
                "",
                "To help with debugging, here are some character position markers:",
                ""
            ])
            
            # Add position markers every 100 characters
            text_length = len(note_text)
            for i in range(0, text_length, 100):
                end_pos = min(i + 100, text_length)
                snippet = note_text[i:end_pos].replace('\n', '\\n')
                lines.append(f"- **{i:4d}-{end_pos:4d}:** `{snippet[:50]}{'...' if len(snippet) > 50 else ''}`")
        
        # Save visualization
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logging.info(f"Span visualization saved to {output_path}")
        return output_path


def main():
    """Example usage of the SpanAnalyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze span overlaps between agent predictions and gold standard')
    parser.add_argument('--agent_csv', required=True, help='Path to agent predictions CSV')
    parser.add_argument('--gold_csv', required=True, help='Path to gold standard CSV')
    parser.add_argument('--notes_csv', help='Path to notes CSV for text extraction')
    parser.add_argument('--output_dir', default='analysis_output', help='Output directory for analysis results')
    parser.add_argument('--iou_threshold', type=float, default=0.5, help='IoU threshold for matching spans')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Initialize analyzer
    analyzer = SpanAnalyzer()
    
    # Load text data if provided
    text_data = {}
    if args.notes_csv:
        text_data = analyzer.load_text_data(args.notes_csv)
    
    # Load spans
    agent_spans = analyzer.load_spans_from_csv(args.agent_csv, "agent", text_data)
    gold_spans = analyzer.load_spans_from_csv(args.gold_csv, "gold", text_data)
    
    logging.info(f"Loaded {len(agent_spans)} agent spans and {len(gold_spans)} gold spans")
    
    # Perform analysis
    results = analyzer.analyze_spans(agent_spans, gold_spans, args.iou_threshold)
    
    # Generate enhanced summary
    summary_path = output_dir / "enhanced_span_analysis.json"
    analyzer.generate_enhanced_summary(results, str(summary_path))
    
    # Create visualizations for each note
    note_ids = set()
    for span in agent_spans + gold_spans:
        note_ids.add(span.note_id)
    
    for note_id in note_ids:
        viz_path = output_dir / f"span_visualization_{note_id}.txt"
        analyzer.create_span_visualization(results, note_id, str(viz_path))
    
    logging.info(f"Analysis complete. Results saved to {output_dir}")


if __name__ == "__main__":
    main()
