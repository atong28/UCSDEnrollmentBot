import faiss
import numpy as np

from ..const import MODEL, COURSES, INDEX

def embed():
    '''
    Generate embeddings and update the course catalog database.
    '''
    embeddings = MODEL.encode([course['desc'] for course in COURSES])
    embeddings_np = np.array(embeddings).astype(np.float32)

    index = faiss.IndexFlatL2(embeddings_np.shape[1])
    index.add(embeddings_np)
    faiss.write_index(index, "data/course_catalog.faiss")

def query(query: str) -> list:
    '''
    Query a string to get list of relevant classes.
    '''
    query_embedding = MODEL.encode([query])
    _, I = INDEX.search(np.array(query_embedding).astype(np.float32), k=len(COURSES))
    results = [COURSES[i] for i in I[0]]
    return results