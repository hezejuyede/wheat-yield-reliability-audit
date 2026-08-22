# Reproduction instructions

Python 3.11+; CPU only. Run `python -m pip install -r 04_CODE/requirements.txt`, then `python 04_CODE/run_all.py`.

The workflow rebuilds the leakage-frozen panel, persistence/ridge/random-forest/gradient-boosting/CAFR predictions, 5,000 paired year-cluster bootstrap replicates, all 21 spatial holdouts, ten-seed random-split audit, routing-harm audit, fixed-capacity review at capacities 0-3, climate subgroup, threshold/history sensitivity, four figures and automated tests. No notebook state, pretrained model, GPU or manually edited result is required.
