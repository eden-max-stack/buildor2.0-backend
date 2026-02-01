from app.services.graph_service import GraphService
from core_engine.gnn.converter import GraphToPyGConverter

code = """
def example(x):
    y = x + 1
    if x > 0:
        z = y * 2
        print(z)
    else:
        z = y * 3
        print(z)
    result = z + y
    return result
"""

# 1. Analysis Layer
service = GraphService(code)
raw_graphs = service.get_raw_graphs() # Get Python Objects

# 2. GNN Processing Layer
converter = GraphToPyGConverter()
gnn_data = converter.convert(raw_graphs) # Get PyTorch Tensor

print(gnn_data)