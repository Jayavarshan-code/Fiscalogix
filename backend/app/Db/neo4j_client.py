from neo4j import GraphDatabase

class Neo4jConnection:
    """
    Enterprise Graph Database Connection.
    Holds the resilient connection pool to the Neo4j Core.
    """
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", pwd="password"):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the Neo4j driver:", e)

    def close(self):
        if self.__driver is not None:
            self.__driver.close()

    def query(self, query, parameters=None, db=None):
        """
        Executes a Cypher query using a managed transaction.
        """
        assert self.__driver is not None, "Neo4j Driver not initialized!"
        session = None
        response = None
        try:
            session = self.__driver.session(database=db) if db is not None else self.__driver.session() 
            response = list(session.run(query, parameters))
        except Exception as e:
            print("Neo4j Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return response

neo4j_client = Neo4jConnection()
