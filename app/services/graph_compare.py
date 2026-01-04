def compare_graphs(student_nodes, ref_nodes):
    error_nodes = []

    ref_types = [n["type"] for n in ref_nodes]

    for node in student_nodes:
        if node["type"] not in ref_types:
            node["status"] = "error"
            error_nodes.append(node["id"])

    return error_nodes
