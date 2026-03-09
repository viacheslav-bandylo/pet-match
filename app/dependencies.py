from app.core.engine import RulesEngine

_engine: RulesEngine | None = None


def init_engine() -> RulesEngine:
    global _engine
    _engine = RulesEngine()
    return _engine


def get_rules_engine() -> RulesEngine:
    assert _engine is not None, "RulesEngine not initialized"
    return _engine
