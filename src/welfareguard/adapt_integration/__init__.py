"""Integration layer between WelfareGuard and ``aisafepy.adapt``.

One module per compiler target. Only ``regex_guard`` (the ``synthesize_regex``
Tier-1 path) exists so far; ``distill_classifier``, ``steering_vector`` and
``deliberative_case`` modules will follow the same shape once ADR-001 is
Accepted.

Nothing here is re-exported. ``welfareguard.guard`` imports these modules
directly — deliberately, since any registry or lookup indirection is itself an
architecture decision and therefore ADR-001's territory, not this scaffold's.
"""
