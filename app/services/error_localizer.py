def classify_error(error_nodes):
    if len(error_nodes) == 0:
        return "NO_ERROR", 1.0

    return "LOGICAL_DEVIATION", 0.8
