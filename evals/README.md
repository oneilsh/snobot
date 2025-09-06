# SNOMED CT Entity Linking Evaluation

This directory contains the evaluation framework for the [SNOMED CT Entity Linking Challenge](https://www.drivendata.org/competitions/258/competition-snomed-ct/) on DrivenData.

## Data Setup

Place the competition data files in `evals/data/snomed_challenge/`:

- `mimic-iv_notes_test_set.csv` - Test set notes
- `mimic-iv_notes_training_set.csv` - Training set notes  
- `test_annotations.csv` - Test set ground truth annotations
- `train_annotations.csv` - Training set ground truth annotations

## Usage

Run evaluation on different data splits:

```bash
# Pre-compute and cache databases (recommended first step)
make precompute-databases

# Prepare smoke test data
make prepare-smoke-data 

# or, to smoke test a smaller number of notes, truncated to the first N gold standard-containing spans
make prepare-smoke-data-custom NOTES=2 CONCEPTS=8

# Run smoke test (subset of training data)
make eval-smoke

# Test on training set with evaluation metrics
make eval-train

# Test on test set with evaluation metrics (final evaluation)
make eval-test
```
