Pipeworks Namegen API
=====================

Overview
========

`pipeworks-namegen-api` is the canonical production service for Pipeworks name generation.
It owns runtime behavior for `/api/generate`, deployment templates, and service operations.

The deterministic generator engine remains in `pipeworks-namegen-core`, while
lexicon/corpus pipeline ownership remains in `pipeworks-namegen-lexicon`.

.. toctree::
   :maxdepth: 2
   :caption: Operations

   deployment
