"""
1. retrieve:
    search: query(context), workspace_id(request), top_k(request)
2. summary:
    insert: nodes(context), workspace_id(request)
    delete: ids(context), workspace_id(request)
    search: query(context), workspace_id(request), top_k(request.config.op)
3. vector:
    dump: workspace_id(request), path(str), max_size(int)
    load: workspace_id(request), path(str)
    delete: workspace_id(request)
    copy: source_id, target_id, max_size(int)
"""
