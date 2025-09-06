"""
Prepare smoke test data for SNOMED CT evaluation
Creates a subset of training data for quick testing
"""

import pandas as pd
import argparse
from pathlib import Path


def prepare_smoke_test_data(num_notes: int = 1, concepts_per_note: int = 6, padding: int = 200):
    """
    Create smoke test data from training set
    
    Args:
        num_notes: Number of notes to include in smoke test
        concepts_per_note: Maximum number of concepts per note
        padding: Characters to add after the last concept
    """
    
    data_dir = Path("evals/data/snomed_challenge")
    
    # Load training data
    train_notes = pd.read_csv(data_dir / "mimic-iv_notes_training_set.csv")
    train_annotations = pd.read_csv(data_dir / "train_annotations.csv")
    
    # Select specified number of notes for smoke test
    smoke_notes = train_notes.head(num_notes).copy()
    smoke_note_ids = set(smoke_notes['note_id'])
    
    # Filter annotations to only include smoke test notes
    smoke_annotations = train_annotations[
        train_annotations['note_id'].isin(smoke_note_ids)
    ].copy()
    
    # For each note, limit to specified number of concepts and truncate text accordingly
    processed_notes = []
    processed_annotations = []
    
    for note_id in smoke_note_ids:
        # Get all annotations for this note
        note_annotations = smoke_annotations[smoke_annotations['note_id'] == note_id].copy()
        
        # Sort by start position and take first N concepts
        note_annotations = note_annotations.sort_values('start').head(concepts_per_note)
        
        if len(note_annotations) == 0:
            continue
            
        # Get the note text
        note_row = smoke_notes[smoke_notes['note_id'] == note_id].iloc[0]
        original_text = note_row['text']
        
        # Find the end position of the last concept
        last_end = note_annotations['end'].max()
        
        # Truncate text to include all concepts with padding
        truncated_text = original_text[:last_end + padding]
        
        # Update the note with truncated text
        processed_notes.append({
            'note_id': note_id,
            'text': truncated_text
        })
        
        # Add the limited annotations
        processed_annotations.append(note_annotations)
    
    # Combine all processed data
    smoke_notes_df = pd.DataFrame(processed_notes)
    smoke_annotations_df = pd.concat(processed_annotations, ignore_index=True)
    
    # Save smoke test data
    smoke_notes_df.to_csv(data_dir / "smoke_test_notes.csv", index=False)
    smoke_annotations_df.to_csv(data_dir / "smoke_test_annotations.csv", index=False)
    
    print(f"Smoke test data prepared:")
    print(f"  Notes: {len(smoke_notes_df)}")
    print(f"  Annotations: {len(smoke_annotations_df)}")
    print(f"  Average concepts per note: {len(smoke_annotations_df) / len(smoke_notes_df) if len(smoke_notes_df) > 0 else 0:.1f}")
    print(f"  Files saved to {data_dir}/")


def main():
    """Command-line interface for preparing smoke test data"""
    parser = argparse.ArgumentParser(description='Prepare smoke test data for SNOMED CT evaluation')
    parser.add_argument('--notes', type=int, default=1,
                       help='Number of notes to include in smoke test (default: 1)')
    parser.add_argument('--concepts', type=int, default=6,
                       help='Maximum number of concepts per note (default: 6)')
    parser.add_argument('--padding', type=int, default=200,
                       help='Characters to add after the last concept (default: 200)')
    
    args = parser.parse_args()
    
    print(f"Preparing smoke test with {args.notes} notes, up to {args.concepts} concepts each...")
    prepare_smoke_test_data(args.notes, args.concepts, args.padding)


if __name__ == "__main__":
    main()
