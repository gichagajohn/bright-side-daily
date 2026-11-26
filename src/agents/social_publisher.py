"""Retired multi-platform entry point.
Facebook publishing now belongs to bsd.pipeline, with durable job claims and QC.
Kept as a fail-closed compatibility guard so old scripts cannot bypass safety.
"""
class SocialPublisher:
    def __init__(self, platforms=None):
        raise RuntimeError('Legacy publishing is disabled. Use src/scheduler.py; see docs/DEPLOYMENT_V2.md')
