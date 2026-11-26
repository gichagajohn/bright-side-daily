"""Bright Side Daily — Facebook-only scheduler.
See docs/DEPLOYMENT_V2.md. No legacy blind retry or multi-platform entry point.
"""
from bsd.pipeline import main
if __name__ == '__main__':
    raise SystemExit(main())
