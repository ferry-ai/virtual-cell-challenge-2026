"""The scientific-research mode: three phases, a structured record, a deterministic dossier.

Separate from the debugging loop on purpose. That loop asks two models to converge on a
proposal; this one asks them to *search*, and the thing that must survive to the end is
not an agreement but a traceable account of what was looked for, what was found, what
supports or contradicts a hypothesis, and what is still unchecked.

Three rules shape the whole package, and each one exists because the opposite is the
easy mistake:

* **A level of provenance is never promoted by code.** A query a worker says it ran is
  recorded as declared by the worker. Nothing turns it into an observed fact except an
  artefact of the channel, and in this version the channel produces none.
* **A syntactically valid reference is not a source that exists.** Sources are recorded
  with what was declared about them and deduplicated only on an identifier -- a DOI or a
  normalised URL -- never on how similar two titles look.
* **The dossier is assembled, not written.** Both syntheses survive verbatim, side by
  side, with their disagreements. No consensus is invented, by code or by a third model.
"""

from .contract import (
    RESEARCH_SENTINEL, Claim, Gap, Hypothesis, Lead, ResearchRecord, Search, Source,
    parse_research_reply,
)
from .engine import ResearchEngine

__all__ = [
    "RESEARCH_SENTINEL", "Claim", "Gap", "Hypothesis", "Lead", "ResearchRecord",
    "ResearchEngine", "Search", "Source", "parse_research_reply",
]
