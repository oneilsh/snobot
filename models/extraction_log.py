"""Extraction process logging models and utilities."""

from pydantic import Field
from pydantic.dataclasses import dataclass
from typing import Optional, Any, Dict, List
from datetime import datetime
import json
import yaml
from dataclasses import asdict


@dataclass
class LogStep:
    """A single step in the extraction process."""
    step_type: str = Field(..., description="Type of step (e.g., 'mention_identification', 'vector_search', 'concept_coding')")
    description: str = Field(..., description="Human-readable description of the step")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this step occurred")
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Input parameters for this step")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="Output results from this step")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata about the step")
    duration_ms: Optional[float] = Field(default=None, description="How long this step took in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if step failed")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        # Convert datetime to ISO string for JSON serialization
        if isinstance(result['timestamp'], datetime):
            result['timestamp'] = result['timestamp'].isoformat()
        return result


@dataclass
class MentionCodingLog:
    """Log for coding a specific mention, containing all sub-steps."""
    mention: str = Field(..., description="The mention being coded")
    steps: List[LogStep] = Field(default_factory=list, description="All steps taken to code this mention")
    final_result: Optional[Dict[str, Any]] = Field(default=None, description="Final coded concept result")
    
    def add_step(self, step: LogStep):
        """Add a step to this mention's coding process."""
        self.steps.append(step)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "mention": self.mention,
            "steps": [step.to_dict() for step in self.steps],
            "final_result": self.final_result
        }


@dataclass
class ExtractionProcessLog:
    """Complete log of the extraction process."""
    input_text: str = Field(..., description="The original input text")
    process_id: str = Field(..., description="Unique identifier for this extraction process")
    start_time: datetime = Field(default_factory=datetime.now, description="When extraction started")
    end_time: Optional[datetime] = Field(default=None, description="When extraction completed")
    steps: List[LogStep] = Field(default_factory=list, description="Top-level process steps")
    mention_logs: List[MentionCodingLog] = Field(default_factory=list, description="Detailed logs for each mention")
    final_results: List[Dict[str, Any]] = Field(default_factory=list, description="Final coded concepts")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Process metadata")
    
    def add_step(self, step: LogStep):
        """Add a top-level step to the process."""
        self.steps.append(step)
    
    def add_mention_log(self, mention_log: MentionCodingLog):
        """Add a mention coding log."""
        self.mention_logs.append(mention_log)
    
    def finalize(self, final_results: List[Dict[str, Any]]):
        """Finalize the log with results."""
        self.end_time = datetime.now()
        self.final_results = final_results
    
    def get_total_duration_ms(self) -> Optional[float]:
        """Calculate total process duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "input_text": self.input_text,
            "process_id": self.process_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.get_total_duration_ms(),
            "steps": [step.to_dict() for step in self.steps],
            "mention_logs": [log.to_dict() for log in self.mention_logs],
            "final_results": self.final_results,
            "metadata": self.metadata
        }
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def to_markdown_report(self) -> str:
        """Generate a markdown report from the log."""
        from utils.report_generator import generate_markdown_report
        return generate_markdown_report(self)


class ExtractionLogger:
    """Logger for tracking extraction process steps."""
    
    def __init__(self, input_text: str, process_id: str):
        self.log = ExtractionProcessLog(
            input_text=input_text,
            process_id=process_id
        )
        self.current_mention_log: Optional[MentionCodingLog] = None
        self._step_start_times: Dict[str, datetime] = {}
    
    def start_step(self, step_id: str, step_type: str, description: str, 
                   input_data: Optional[Dict[str, Any]] = None) -> str:
        """Start timing a step and return the step ID."""
        self._step_start_times[step_id] = datetime.now()
        return step_id
    
    def log_step(self, step_type: str, description: str, 
                 input_data: Optional[Dict[str, Any]] = None,
                 output_data: Optional[Dict[str, Any]] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None,
                 step_id: Optional[str] = None) -> LogStep:
        """Log a completed step."""
        
        # Calculate duration if we have a start time
        duration_ms = None
        if step_id and step_id in self._step_start_times:
            start_time = self._step_start_times[step_id]
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            del self._step_start_times[step_id]
        
        step = LogStep(
            step_type=step_type,
            description=description,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata,
            duration_ms=duration_ms,
            error=error
        )
        
        # Add to current mention log if we're coding a mention, otherwise to main log
        if self.current_mention_log:
            self.current_mention_log.add_step(step)
        else:
            self.log.add_step(step)
        
        return step
    
    def start_mention_coding(self, mention: str) -> MentionCodingLog:
        """Start logging for a specific mention coding process."""
        self.current_mention_log = MentionCodingLog(mention=mention)
        return self.current_mention_log
    
    def finish_mention_coding(self, final_result: Optional[Dict[str, Any]] = None):
        """Finish logging for the current mention."""
        if self.current_mention_log:
            self.current_mention_log.final_result = final_result
            self.log.add_mention_log(self.current_mention_log)
            self.current_mention_log = None
    
    def finalize(self, final_results: List[Dict[str, Any]]):
        """Finalize the extraction log."""
        self.log.finalize(final_results)
    
    def get_log(self) -> ExtractionProcessLog:
        """Get the current log."""
        return self.log
