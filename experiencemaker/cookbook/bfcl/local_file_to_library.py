import json
with open("../../file_vector_store/bfcl_train50_qwen3_mix_32b&8b&14b_extract_compare_validate_categorized-noshuffle.jsonl", 'r') as f:
    appworld = [json.loads(line) for line in f]
    
new_appworld = []
for exp in appworld:
    new_exp = {}
    new_exp["workspace_id"] = exp["workspace_id"]
    new_exp["experience_id"] = exp["unique_id"]
    new_exp["experience_type"] = "text"
    # new_exp["when_to_use"] = exp["content"]
    new_exp["when_to_use"] = exp["metadata"]["when_to_use"]
    new_exp["task_query"] = exp["metadata"]["task_query"]
    new_exp["content"] = exp["metadata"]["experience_content"]
    new_exp["score"] =  exp["metadata"]["score"]
    new_exp["metadata"]= exp["metadata"]["metadata"]

    new_appworld.append(new_exp)
    
    

with open('../../experiment_library/bfcl_train50_qwen3_mix_32b&8b&14b_extract_compare_validate_categorized-noshuffle.jsonl', 'w', encoding='utf-8') as f:
   f.writelines(json.dumps(item, ensure_ascii=False) + '\n' for item in new_appworld)