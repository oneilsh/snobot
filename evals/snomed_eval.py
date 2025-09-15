"""
SNOMED CT Entity Linking Evaluation Framework
Integrates with the DrivenData competition runtime format
"""

import os
import sys
import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
import numpy as np

# Add the project root to the path so we can import snobot modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.extract_agent import extract_and_code_mentions
from models.model_config import get_model_config, DEFAULT_MODEL
from utils.report_generator import generate_markdown_report, generate_summary_stats
# Import database classes directly to avoid Streamlit warnings
from resources.sql_db import SqlDB
from resources.vec_db import VecDB
# Import official DrivenData scoring function
from evals.scoring import iou_per_class
# Import enhanced span analyzer
from evals.span_analyzer import SpanAnalyzer


class SNOMEDEvaluator:
    """
    Evaluator class that adapts the SNOBot framework to the SNOMED CT competition format
    """
    
    def __init__(self, data_dir: str = "evals/data/snomed_challenge"):
        self.data_dir = Path(data_dir)
        self.model_config = get_model_config(DEFAULT_MODEL)
        self.vec_db = None
        self.sql_db = None
        self.span_analyzer = None
        # Will be set properly when we know the split
        self.reports_dir = None
        
    def initialize_resources(self):
        """Initialize the vector database and SQL database resources"""
        try:
            self.vec_db = VecDB()
            self.sql_db = SqlDB()
            self.span_analyzer = SpanAnalyzer(sql_db=self.sql_db)
            logging.info("Resources initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize resources: {e}")
            raise
    
    def setup_output_directories(self, split: str, output_path: str):
        """Setup output directories based on split and output path"""
        output_path_obj = Path(output_path)
        output_dir = output_path_obj.parent
        
        # Create the reports directory in the same location as the output
        self.reports_dir = output_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"Reports will be saved to {self.reports_dir}")
    
    def load_data(self, split: str = "test") -> pd.DataFrame:
        """Load the competition data files"""
        # Handle smoke test explicitly
        if split == "smoke":
            smoke_test_file = self.data_dir / "smoke_test_notes.csv"
            if smoke_test_file.exists():
                df = pd.read_csv(smoke_test_file)
                logging.info(f"Loaded {len(df)} notes from smoke test set")
                return df
            else:
                raise FileNotFoundError(f"Smoke test file not found: {smoke_test_file}")
        
        # Load the full dataset
        if split == "test":
            notes_file = self.data_dir / "mimic-iv_notes_test_set.csv"
        elif split == "train":
            notes_file = self.data_dir / "mimic-iv_notes_training_set.csv"
        else:
            raise ValueError(f"Unknown split: {split}. Use 'test', 'train', or 'smoke'")
            
        if not notes_file.exists():
            raise FileNotFoundError(f"Data file not found: {notes_file}")
            
        df = pd.read_csv(notes_file)
        logging.info(f"Loaded {len(df)} notes from {split} set")
        return df
    
    def load_annotations(self, split: str = "test") -> pd.DataFrame:
        """Load the ground truth annotations"""
        # Handle smoke test explicitly
        if split == "smoke":
            smoke_test_annotations = self.data_dir / "smoke_test_annotations.csv"
            if smoke_test_annotations.exists():
                df = pd.read_csv(smoke_test_annotations)
                logging.info(f"Loaded {len(df)} annotations from smoke test set")
                return df
            else:
                raise FileNotFoundError(f"Smoke test annotations not found: {smoke_test_annotations}")
        
        # Load the full dataset
        if split == "test":
            annotations_file = self.data_dir / "test_annotations.csv"
        elif split == "train":
            annotations_file = self.data_dir / "train_annotations.csv"
        else:
            raise ValueError(f"Unknown split: {split}. Use 'test', 'train', or 'smoke'")
            
        if not annotations_file.exists():
            raise FileNotFoundError(f"Annotations file not found: {annotations_file}")
            
        df = pd.read_csv(annotations_file)
        logging.info(f"Loaded {len(df)} annotations from {split} set")
        return df
    
    def extract_entities(self, text: str, note_id: str = None) -> List[Dict[str, Any]]:
        """
        Extract SNOMED CT entities from text using the SNOBot framework
        Returns entities in the format expected by the competition
        
        This implementation:
        1. Finds all occurrences of each mention in the text (not just first)
        2. Maps OMOP concept_ids to SNOMED concept_codes for competition compatibility
        3. Resolves overlapping spans to ensure non-overlapping output
        """
        try:
            # Use the extract function directly - status_widget can be None
            coded_concepts, extraction_logger = extract_and_code_mentions(text, None)
            
            # Save extraction report as JSON
            self._save_extraction_report(extraction_logger, text, note_id=note_id)
            
            # Convert to competition format with robust string matching
            # This approach is correct: AI codes deduplicated mentions, then we find all occurrences
            # The key is handling case/whitespace variations properly
            competition_entities = []
            for concept in coded_concepts:
                mention_str = concept.mention_str
                
                # Get SNOMED concept_code instead of OMOP concept_id
                snomed_code = self._get_snomed_code_from_omop_id(concept.concept_id)
                
                if snomed_code:  # Only proceed if we can map to SNOMED code
                    # Find ALL occurrences of the mention, handling case and whitespace variations
                    occurrences = self._find_all_mention_occurrences(text, mention_str)
                    
                    for start_pos, end_pos in occurrences:
                        competition_entities.append({
                            'start': start_pos,
                            'end': end_pos,
                            'text': text[start_pos:end_pos],  # Use actual text span
                            'concept_id': int(snomed_code),  # Competition expects SNOMED code as integer
                            'omop_concept_id': int(concept.concept_id)  # Keep for debugging
                        })
            
            # Resolve overlapping spans to ensure non-overlapping output
            competition_entities = self._resolve_overlapping_spans(competition_entities)
            
            # Remove debugging field for final output
            for entity in competition_entities:
                entity.pop('omop_concept_id', None)
            
            return competition_entities
            
        except Exception as e:
            logging.error(f"Error extracting entities from text: {e}")
            return []
    
    def _find_all_mention_occurrences(self, text: str, mention_str: str) -> List[Tuple[int, int]]:
        """
        Find all occurrences of a mention in text, handling case and whitespace variations.
        
        This handles cases like:
        - "Biliary pancreatitis" vs "biliary pancreatitis" (case)
        - "biliary pancreatitis" vs "biliary \npancreatitis" (whitespace)
        
        Returns list of (start_pos, end_pos) tuples.
        """
        import re
        
        # Escape special regex characters in the mention
        escaped_mention = re.escape(mention_str)
        
        # Replace spaces in the pattern with flexible whitespace matcher
        # This matches any sequence of whitespace characters (space, tab, newline, etc.)
        flexible_pattern = escaped_mention.replace(r'\ ', r'\s+')
        
        # Case-insensitive search
        pattern = re.compile(flexible_pattern, re.IGNORECASE)
        
        occurrences = []
        for match in pattern.finditer(text):
            occurrences.append((match.start(), match.end()))
        
        return occurrences
    
    def _get_snomed_code_from_omop_id(self, omop_concept_id: str) -> str:
        """
        Map OMOP concept_id to SNOMED concept_code using the SQL database
        Returns the SNOMED concept_code if found, None otherwise
        """
        try:
            # Query the concept table to get the SNOMED code
            sql_query = f"SELECT concept_code, vocabulary_id FROM concept WHERE concept_id = {omop_concept_id}"
            query_result = self.sql_db.run_query(sql_query)
            
            if query_result and len(query_result) > 0:
                concept_code, vocabulary_id = query_result[0]
                
                # Only return codes from SNOMED vocabularies
                if vocabulary_id in ['SNOMED', 'SNOMEDCT_US']:
                    return str(concept_code)
                else:
                    logging.warning(f"Concept {omop_concept_id} is not from SNOMED vocabulary (found: {vocabulary_id})")
                    return None
            else:
                logging.warning(f"No concept found for OMOP ID {omop_concept_id}")
                return None
                
        except Exception as e:
            logging.error(f"Error mapping OMOP ID {omop_concept_id} to SNOMED code: {e}")
            return None
    
    def _resolve_overlapping_spans(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolve overlapping spans by keeping the longest span for each overlap
        This ensures non-overlapping spans as required by the competition
        """
        if not entities:
            return entities
        
        # Sort entities by start position, then by length (longest first for same start)
        sorted_entities = sorted(entities, key=lambda x: (x['start'], -(x['end'] - x['start'])))
        
        non_overlapping = []
        for entity in sorted_entities:
            # Check if this entity overlaps with any already selected entity
            overlaps = False
            for selected in non_overlapping:
                if self._spans_overlap(entity, selected):
                    overlaps = True
                    break
            
            if not overlaps:
                non_overlapping.append(entity)
        
        return non_overlapping
    
    def _spans_overlap(self, span1: Dict[str, Any], span2: Dict[str, Any]) -> bool:
        """Check if two spans overlap"""
        return not (span1['end'] <= span2['start'] or span2['end'] <= span1['start'])
    
    def _save_extraction_report(self, extraction_logger, text: str, note_id: str = None):
        """Save extraction report as JSON and markdown."""
        try:
            # Skip saving if reports directory is not set up
            if self.reports_dir is None:
                logging.warning("Reports directory not set up, skipping report save")
                return
                
            # Get the extraction log
            log = extraction_logger.get_log()
            
            # Generate filename based on note_id if provided, otherwise use process ID and timestamp
            if note_id:
                base_filename = f"{note_id}_report"
            else:
                timestamp = log.start_time.strftime("%Y%m%d_%H%M%S")
                base_filename = f"extraction_{log.process_id}_{timestamp}"
            
            # Save JSON report
            json_path = self.reports_dir / f"{base_filename}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(log.to_json(indent=2))
            
            # Save markdown report
            markdown_path = self.reports_dir / f"{base_filename}.md"
            markdown_report = generate_markdown_report(log)
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_report)
            
            # Log cost information
            usage_stats = log.get_usage_statistics()
            if usage_stats['total_requests'] > 0:
                logging.info(f"Extraction completed - Cost: ${usage_stats['total_cost']:.4f}, "
                           f"Tokens: {usage_stats['total_tokens']:,}, "
                           f"Reports saved: {json_path.name}, {markdown_path.name}")
            else:
                logging.info(f"Extraction completed - Reports saved: {json_path.name}, {markdown_path.name}")
                
        except Exception as e:
            logging.error(f"Error saving extraction report: {e}")
    
    def process_notes(self, notes_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Process all notes and extract entities
        Returns results in competition submission format
        """
        results = []
        
        for idx, row in notes_df.iterrows():
            note_id = row['note_id']
            text = row['text']
            
            logging.info(f"Processing note {note_id} ({idx + 1}/{len(notes_df)})")
            
            entities = self.extract_entities(text, note_id=note_id)
            
            for entity in entities:
                results.append({
                    'note_id': note_id,
                    'start': entity['start'],
                    'end': entity['end'],
                    'concept_id': entity['concept_id']
                })
        
        return results
    
    def create_submission_file(self, results: List[Dict[str, Any]], output_path: str = "submission.csv"):
        """Create submission file in the required format"""
        df = pd.DataFrame(results)
        
        # Ensure required columns are present (competition format: note_id, start, end, concept_id)
        required_columns = ['note_id', 'start', 'end', 'concept_id']
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Reorder columns to match expected format
        df = df[required_columns]
        
        # Ensure concept_id is integer
        df['concept_id'] = df['concept_id'].astype(int)
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        logging.info(f"Submission file saved to {output_path} with {len(df)} entries")
        
        return output_path
    
    def evaluate_submission(self, submission_path: str, ground_truth_path: str) -> Dict[str, float]:
        """
        Evaluate submission against ground truth using IoU metrics
        Uses the EXACT official DrivenData scoring.py implementation
        """
        try:
            submission_df = pd.read_csv(submission_path)
            ground_truth_df = pd.read_csv(ground_truth_path)
            
            logging.info(f"Evaluating {len(submission_df)} predictions against {len(ground_truth_df)} ground truth annotations")
            
            # Use official DrivenData implementation directly from their scoring.py
            class_ious = iou_per_class(submission_df, ground_truth_df)
            
            # Macro-average IoU across all classes (as specified in competition)
            macro_avg_iou = sum(class_ious) / len(class_ious) if class_ious else 0
            
            # Calculate traditional metrics for comparison (using our existing logic)
            total_matches = 0
            total_predictions = len(submission_df)
            total_ground_truth = len(ground_truth_df)
            
            # Get all concept_ids for traditional metrics calculation
            all_concept_ids = set(submission_df['concept_id'].unique()) | set(ground_truth_df['concept_id'].unique())
            for concept_id in all_concept_ids:
                concept_pred = submission_df[submission_df['concept_id'] == concept_id]
                concept_gt = ground_truth_df[ground_truth_df['concept_id'] == concept_id]
                total_matches += self._count_matches_for_class(concept_pred, concept_gt)
            
            precision = total_matches / total_predictions if total_predictions > 0 else 0
            recall = total_matches / total_ground_truth if total_ground_truth > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            # Create class_ious dict for JSON serialization
            cats = np.unique(np.concatenate([submission_df['concept_id'], ground_truth_df['concept_id']]))
            class_ious_dict = {str(cat): iou for cat, iou in zip(cats, class_ious)}
            
            metrics = {
                'macro_avg_iou': macro_avg_iou,  # Primary competition metric
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'total_predictions': total_predictions,
                'total_ground_truth': total_ground_truth,
                'total_matches': total_matches,
                'num_classes': len(class_ious),
                'class_ious': class_ious_dict
            }
            
            logging.info(f"Evaluation metrics - IoU: {macro_avg_iou:.4f}, F1: {f1:.4f}, Classes: {len(class_ious)}")
            return metrics
            
        except Exception as e:
            logging.error(f"Error evaluating submission: {e}")
            return {}
    
    def _calculate_class_iou(self, pred_df: pd.DataFrame, gt_df: pd.DataFrame) -> float:
        """
        Calculate IoU for a specific concept class
        IoU = intersection / union of character spans
        """
        if len(pred_df) == 0 and len(gt_df) == 0:
            return 1.0  # Perfect match if both are empty
        if len(pred_df) == 0 or len(gt_df) == 0:
            return 0.0  # No match if one is empty
        
        total_intersection = 0
        total_union = 0
        
        # Group by note_id to calculate IoU per note, then average
        note_ious = []
        all_notes = set(pred_df['note_id'].unique()) | set(gt_df['note_id'].unique())
        
        for note_id in all_notes:
            note_pred = pred_df[pred_df['note_id'] == note_id]
            note_gt = gt_df[gt_df['note_id'] == note_id]
            
            # Create character sets for this note
            pred_chars = set()
            for _, row in note_pred.iterrows():
                pred_chars.update(range(row['start'], row['end']))
            
            gt_chars = set()
            for _, row in note_gt.iterrows():
                gt_chars.update(range(row['start'], row['end']))
            
            # Calculate IoU for this note
            intersection = len(pred_chars & gt_chars)
            union = len(pred_chars | gt_chars)
            
            if union > 0:
                note_iou = intersection / union
                note_ious.append(note_iou)
        
        # Return average IoU across notes for this class
        return sum(note_ious) / len(note_ious) if note_ious else 0.0
    
    def _count_matches_for_class(self, pred_df: pd.DataFrame, gt_df: pd.DataFrame) -> int:
        """Count approximate matches for traditional metrics"""
        matches = 0
        for _, pred_row in pred_df.iterrows():
            for _, gt_row in gt_df.iterrows():
                if (pred_row['note_id'] == gt_row['note_id'] and
                    self._spans_have_significant_overlap(pred_row, gt_row)):
                    matches += 1
                    break  # Count each prediction at most once
        return matches
    
    def _spans_have_significant_overlap(self, span1: Dict, span2: Dict, threshold: float = 0.5) -> bool:
        """Check if two spans have significant overlap (>= threshold IoU)"""
        start1, end1 = span1['start'], span1['end']
        start2, end2 = span2['start'], span2['end']
        
        intersection = max(0, min(end1, end2) - max(start1, start2))
        union = max(end1, end2) - min(start1, start2)
        
        if union == 0:
            return start1 == start2 and end1 == end2  # Both are zero-length at same position
        
        return (intersection / union) >= threshold
    
    def generate_summary_report(self, results: List[Dict[str, Any]], metrics: Dict[str, float], split: str, submission_path: str):
        """Generate a comprehensive summary report combining all individual reports with enhanced span analysis."""
        try:
            import json
            from pathlib import Path
            from datetime import datetime
            
            # Collect all individual reports
            individual_reports = []
            total_cost = 0.0
            total_tokens = 0
            total_requests = 0
            step_type_counts = {}
            total_mentions = 0
            total_concepts = 0
            
            # Process each unique note's report (avoid duplicates)
            processed_notes = set()
            for result in results:
                note_id = result['note_id']
                if note_id in processed_notes:
                    continue
                processed_notes.add(note_id)
                
                report_files = list(self.reports_dir.glob(f"{note_id}_report.json"))
                
                if report_files:
                    report_file = report_files[0]
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    individual_reports.append({
                        'note_id': note_id,
                        'report_file': str(report_file),
                        'summary': {
                            'mentions_identified': len(report_data.get('mention_logs', [])),
                            'concepts_coded': len(report_data.get('final_results', [])),
                            'total_duration_ms': report_data.get('total_duration_ms', 0),
                            'text_length': len(report_data.get('input_text', ''))
                        }
                    })
                    
                    # Aggregate usage statistics from the log data
                    usage_stats = report_data.get('usage_statistics', {})
                    if usage_stats:
                        total_cost += usage_stats.get('total_cost', 0)
                        total_tokens += usage_stats.get('total_tokens', 0)
                        total_requests += usage_stats.get('total_requests', 0)
                    else:
                        # Fallback: calculate from individual steps
                        for step in report_data.get('steps', []):
                            if 'usage_stats' in step.get('output_data', {}):
                                usage = step['output_data']['usage_stats']
                                total_cost += self.model_config.calculate_cost(
                                    usage.get('request_tokens', 0),
                                    usage.get('response_tokens', 0)
                                )
                                total_tokens += usage.get('total_tokens', 0)
                                total_requests += usage.get('requests', 0)
                        
                        for mention_log in report_data.get('mention_logs', []):
                            for step in mention_log.get('steps', []):
                                if 'usage_stats' in step.get('output_data', {}):
                                    usage = step['output_data']['usage_stats']
                                    total_cost += self.model_config.calculate_cost(
                                        usage.get('request_tokens', 0),
                                        usage.get('response_tokens', 0)
                                    )
                                    total_tokens += usage.get('total_tokens', 0)
                                    total_requests += usage.get('requests', 0)
                    
                    # Count step types
                    for mention_log in report_data.get('mention_logs', []):
                        total_mentions += 1
                        for step in mention_log.get('steps', []):
                            step_type = step.get('step_type', 'unknown')
                            step_type_counts[step_type] = step_type_counts.get(step_type, 0) + 1
                    
                    total_concepts += len(report_data.get('final_results', []))
            
            # Run enhanced span analysis
            enhanced_analysis = self._run_enhanced_span_analysis(submission_path, split, results)
            
            # Create comprehensive summary with enhanced span analysis
            summary_report = {
                'evaluation_summary': {
                    'split': split,
                    'timestamp': datetime.now().isoformat(),
                    'total_notes_processed': len(individual_reports),
                    'total_mentions_identified': total_mentions,
                    'total_concepts_coded': total_concepts,
                    'evaluation_metrics': metrics
                },
                'enhanced_span_analysis': enhanced_analysis,
                'cost_analysis': {
                    'total_cost_usd': round(total_cost, 4),
                    'total_tokens': total_tokens,
                    'total_api_requests': total_requests,
                    'avg_cost_per_note': round(total_cost / len(individual_reports), 4) if individual_reports else 0,
                    'avg_tokens_per_note': round(total_tokens / len(individual_reports), 0) if individual_reports else 0
                },
                'processing_analysis': {
                    'step_type_counts': step_type_counts,
                    'avg_mentions_per_note': round(total_mentions / len(individual_reports), 1) if individual_reports else 0,
                    'avg_concepts_per_note': round(total_concepts / len(individual_reports), 1) if individual_reports else 0
                },
                'individual_reports': individual_reports
            }
            
            # Generate appropriate summary filename based on split and submission path
            submission_path_obj = Path(submission_path)
            summary_filename = f"{split}_evaluation_summary.json"
            summary_path = submission_path_obj.parent / summary_filename
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Comprehensive summary report saved to {summary_path}")
            logging.info(f"Summary: {len(individual_reports)} notes, ${total_cost:.4f} cost, {total_tokens:,} tokens")
            
        except Exception as e:
            logging.error(f"Error generating summary report: {e}")
    
    def _run_enhanced_span_analysis(self, submission_path: str, split: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run enhanced span analysis and return results"""
        try:
            # Load the notes data to get text for span analysis
            notes_df = self.load_data(split=split)
            text_data = {}
            for _, row in notes_df.iterrows():
                text_data[str(row['note_id'])] = str(row['text'])
            
            # Load annotations data
            annotations_df = self.load_annotations(split=split)
            
            # Create temporary annotations file for span analyzer
            submission_path_obj = Path(submission_path)
            temp_annotations_path = submission_path_obj.parent / f"temp_{split}_annotations.csv"
            annotations_df.to_csv(temp_annotations_path, index=False)
            
            # Load spans using the analyzer
            agent_spans = self.span_analyzer.load_spans_from_csv(submission_path, "agent", text_data)
            gold_spans = self.span_analyzer.load_spans_from_csv(str(temp_annotations_path), "gold", text_data)
            
            logging.info(f"Enhanced span analysis: {len(agent_spans)} agent spans, {len(gold_spans)} gold spans")
            
            # Perform comprehensive span analysis
            analysis_results = self.span_analyzer.analyze_spans(agent_spans, gold_spans, iou_threshold=0.5)
            
            # Save detailed analysis
            output_dir = submission_path_obj.parent
            enhanced_summary_path = output_dir / f"{split}_detailed_span_analysis.json"
            self.span_analyzer.generate_enhanced_summary(analysis_results, str(enhanced_summary_path))
            
            # Create visualizations for each note
            note_ids = set()
            for span in agent_spans + gold_spans:
                note_ids.add(span.note_id)
            
            visualizations_dir = output_dir / "span_visualizations"
            visualizations_dir.mkdir(exist_ok=True)
            
            for note_id in note_ids:
                viz_path = visualizations_dir / f"spans_{note_id}.md"
                try:
                    # Get the note text for this note_id
                    note_text = text_data.get(note_id, "")
                    self.span_analyzer.create_span_visualization(analysis_results, note_id, str(viz_path), note_text)
                except Exception as e:
                    logging.warning(f"Could not create visualization for note {note_id}: {e}")
            
            # Clean up temporary file
            temp_annotations_path.unlink()
            
            # Return summary for inclusion in main report
            stats = analysis_results["statistics"]
            return {
                "summary": {
                    "total_agent_spans": stats["total_agent_spans"],
                    "total_gold_spans": stats["total_gold_spans"],
                    "exact_matches": stats["exact_matches"],
                    "partial_overlaps": stats["partial_overlaps"],
                    "concept_mismatches": stats["concept_mismatches"],
                    "agent_only_spans": stats["agent_only_spans"],
                    "gold_only_spans": stats["gold_only_spans"],
                    "span_precision": stats["exact_matches"] / stats["total_agent_spans"] if stats["total_agent_spans"] > 0 else 0,
                    "span_recall": stats["exact_matches"] / stats["total_gold_spans"] if stats["total_gold_spans"] > 0 else 0
                },
                "detailed_analysis_file": str(enhanced_summary_path.relative_to(output_dir)),
                "visualizations_directory": str(visualizations_dir.relative_to(output_dir)),
                "top_performing_concepts": self._get_top_performing_concepts(stats["by_concept_id"]),
                "missed_concepts": self._get_missed_concepts(stats["by_concept_id"])
            }
            
        except Exception as e:
            logging.error(f"Error running enhanced span analysis: {e}")
            return {
                "summary": {"error": f"Span analysis failed: {str(e)}"},
                "detailed_analysis_file": None,
                "visualizations_directory": None
            }
    
    def _get_top_performing_concepts(self, concept_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get top performing concepts (perfect recall and precision)"""
        top_concepts = []
        for concept_id, stats in concept_stats.items():
            if (stats["gold_count"] > 0 and stats["agent_count"] > 0 and 
                stats["matches"] == stats["gold_count"] and stats["matches"] == stats["agent_count"]):
                top_concepts.append({
                    "concept_id": concept_id,
                    "concept_name": stats["concept_name"],
                    "perfect_matches": stats["matches"]
                })
        
        # Sort by number of perfect matches
        top_concepts.sort(key=lambda x: x["perfect_matches"], reverse=True)
        return top_concepts[:5]  # Return top 5
    
    def _get_missed_concepts(self, concept_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get concepts that were completely missed"""
        missed_concepts = []
        for concept_id, stats in concept_stats.items():
            if stats["gold_count"] > 0 and stats["matches"] == 0:
                missed_concepts.append({
                    "concept_id": concept_id,
                    "concept_name": stats["concept_name"],
                    "missed_instances": stats["gold_count"]
                })
        
        # Sort by number of missed instances
        missed_concepts.sort(key=lambda x: x["missed_instances"], reverse=True)
        return missed_concepts[:5]  # Return top 5 missed


def main():
    """Main function for running evaluation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SNOMED CT Entity Linking Evaluation')
    parser.add_argument('--data_dir', default='evals/data/snomed_challenge', 
                       help='Directory containing competition data')
    parser.add_argument('--split', default='test', choices=['test', 'train', 'smoke'],
                       help='Data split to process')
    parser.add_argument('--output', default='submission.csv',
                       help='Output file for submission')
    parser.add_argument('--evaluate', action='store_true',
                       help='Evaluate submission against ground truth')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize evaluator
    evaluator = SNOMEDEvaluator(data_dir=args.data_dir)
    
    try:
        # Initialize resources
        evaluator.initialize_resources()
        
        # Setup output directories
        evaluator.setup_output_directories(args.split, args.output)
        
        # Load data
        notes_df = evaluator.load_data(split=args.split)
        
        # Process notes
        results = evaluator.process_notes(notes_df)
        
        # Create submission file
        submission_path = evaluator.create_submission_file(results, args.output)
        
        # Evaluate if requested
        if args.evaluate:
            # Load annotations using the same split logic
            annotations_df = evaluator.load_annotations(split=args.split)
            
            # Save annotations to temporary file for evaluation function
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
                annotations_df.to_csv(tmp_file.name, index=False)
                gt_path = tmp_file.name
            
            metrics = evaluator.evaluate_submission(submission_path, gt_path)
            print(f"Evaluation metrics: {metrics}")
            
            # Generate comprehensive summary report with proper naming
            evaluator.generate_summary_report(results, metrics, args.split, args.output)
            
            # Clean up temporary file
            import os
            os.unlink(gt_path)
        
        print(f"Evaluation complete. Submission saved to {submission_path}")
        
    except Exception as e:
        logging.error(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
