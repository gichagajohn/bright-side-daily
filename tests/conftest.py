import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*a,**kw): raise AssertionError('Network disabled in regression tests')
    monkeypatch.setattr('requests.sessions.Session.request',blocked)
