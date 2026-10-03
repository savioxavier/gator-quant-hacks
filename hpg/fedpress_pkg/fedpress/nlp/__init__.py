"""Text helpers for the ``text`` stage and the stance training step: sentence splitting, statement parsing,
dictionaries (Loughran-McDonald, hedges, TDW keyword filter), sequence-classifier scoring and novelty vectors.

Everything here is deterministic given the pinned versions; heavy libraries (torch, transformers,
sentence-transformers) are imported inside the functions that need them.
"""
