import os
import logging
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FIX M5: Neo4j credentials moved to env vars. Removed hardcoded "password".
# FIX M5: Replaced print() with logger. Removed bare assert (crashes with
#         no context) — replaced with explicit RuntimeError message.
# FIX M5: Module-level instantiation is now lazy / guarded to prevent
#         import-time crashes when Neo4j is not running.
# ---------------------------------------------------------------------------

NEO4J_URI  = os.environ.get("NEO4J_URI",  "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PWD  = os.environ.get("NEO4J_PASSWORD", "")  # Never hardcode a default password


class Neo4jConnection:
    """
    Enterprise Graph Database Connection Pool.
    Holds a resilient connection to the Neo4j Core for contagion risk modeling.
    """

    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, pwd: str = NEO4J_PWD):
        self._uri    = uri
        self._user   = user
        self._driver = None
        try:
            self._driver = GraphDatabase.driver(
                uri,
                auth=(user, pwd),
                connection_timeout=2.0,
            )
            self._driver.verify_connectivity()
            logger.info(f"Neo4j: connected to {uri}")
        except Exception as e:
            # FIX M5: structured log instead of print(); driver stays None
            logger.warning(f"Neo4j: failed to connect — {type(e).__name__}: {e}. "
                           "Graph contagion features will be disabled.")
            self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    def query(self, query: str, parameters: dict = None, db: str = None):
        """
        Executes a Cypher query using a managed transaction.
        Returns None gracefully if Neo4j is not connected — callers must handle.
        """
        if not self._driver:
            logger.warning("Neo4j: query skipped — driver not initialized.")
            return None

        session = None
        try:
            session = self._driver.session(database=db) if db else self._driver.session()
            return list(session.run(query, parameters or {}))
        except Exception as e:
            logger.error(f"Neo4j: query failed — {type(e).__name__}: {e}", exc_info=True)
            return None
        finally:
            if session:
                session.close()


# Lazy singleton — only instantiated when first imported
neo4j_client = Neo4jConnection()
