import json
import requests
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


def load_task_case(data_path: str, task_id: str | None) -> Dict[str, Any]:
    """按 ID加载单条 JSONL 训练用例。找不到就抛错。"""
    if not Path(data_path).exists():
        raise FileNotFoundError(f"BFCL data file '{data_path}' not found")

    if task_id is None:
        raise ValueError("task_id is required")

    with open(data_path, "r", encoding="utf-8") as f:
        if str(task_id).isdigit():
            idx = int(task_id)
            for line_no, line in enumerate(f):
                if line_no == idx:
                    return json.loads(line)
            raise ValueError(f"Task case index {idx} not found in {data_path}")
        else:
            for line in f:
                data = json.loads(line)
                if data.get("id") == task_id:
                    return data
            raise ValueError(f"Task case id '{task_id}' not found in {data_path}")


def get_tool_prompt(tools):
    tool_prompt = "\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>"
    for tool in tools:
        tool_prompt += "\n" + json.dumps(tool)
    tool_prompt += "\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>"
    return tool_prompt


def group_trajectories_by_task_id(jsonl_entries: List[Dict[str, Any]]) -> List[List[Any]]:
    """
    根据task_id字段对trajectories进行分组
    
    Args:
        jsonl_entries: JSONL条目列表
        
    Returns:
        List[List[Any]]: 按task_id分组的trajectory列表
    """
    # 按task_id分组
    grouped = defaultdict(list)
    
    for entry in jsonl_entries:
        task_id = entry.get("task_id", "")
        taks_case = load_task_case("data/multiturn_data_base.jsonl", task_id)
        tools = taks_case.get("tools", [{}])
        from bfcl_utils import extract_tool_schema
        tool_schema = extract_tool_schema(tools)
        entry["task_history"][0]["content"] += get_tool_prompt(tool_schema)
        grouped[task_id].append(entry)
    
    # 对每组只保留最大和最小reward的两个
    filtered_groups = []
    for key, trajectories in grouped.items():
        if len(trajectories) == 1:
            # 只有一个trajectory，直接保留
            filtered_groups.append(trajectories)
        elif len(trajectories) == 2:
            # 有两个trajectory，直接保留
            filtered_groups.append(trajectories)
        else:
            # 多个trajectory，选择最大和最小reward的
            # import random
            # random.shuffle(trajectories)
            trajectories.sort(key=lambda t: t["reward"])
            min_reward_traj = trajectories[0]  # 最小reward
            max_reward_traj = trajectories[-1]  # 最大reward
            filtered_groups.append([min_reward_traj, max_reward_traj])
    
    return filtered_groups


def post_to_summarizer(trajectories: List[Any], service_url: str, workspace_id: str) -> Dict[str, Any]:
    """
    将trajectories发送到summarizer服务
    
    Args:
        trajectories: trajectory列表
        service_url: 服务URL
        workspace_id: 工作空间ID
        
    Returns:
        响应结果
    """
    trajectory_dicts = [{
        "task_id": traj["task_id"],
        "messages": traj["task_history"],
        "score": traj["reward"]
    } for traj in trajectories]

    request_data = {
        "traj_list": trajectory_dicts,
        "workspace_id": workspace_id
    }
    
    try:
        response = requests.post(f"{service_url}/summarizer", json=request_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "trajectories_count": len(trajectories)}


def process_trajectories_with_threads(grouped_trajectories: List[List[Any]], 
                                    service_url: str, 
                                    workspace_id: str, 
                                    n_threads: int = 4) -> List[Dict[str, Any]]:
    """
    使用多线程处理trajectories组
    
    Args:
        grouped_trajectories: 按task_id分组的trajectory列表
        service_url: summarizer服务URL
        workspace_id: 工作空间ID
        n_threads: 线程数
        
    Returns:
        所有结果列表
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        # 提交所有任务
        future_to_group = {
            executor.submit(post_to_summarizer, group, service_url, workspace_id): i 
            for i, group in enumerate(grouped_trajectories)
        }
        
        # 收集结果
        for future in as_completed(future_to_group):
            group_index = future_to_group[future]
            try:
                result = future.result()
                result["group_index"] = group_index
                result["group_size"] = len(grouped_trajectories[group_index])
                results.append(result)
                print(f"✅ Group {group_index} processed: {result.get('experience_list', 0) if 'experience_list' in result else 'error'}")
            except Exception as e:
                error_result = {
                    "group_index": group_index,
                    "group_size": len(grouped_trajectories[group_index]),
                    "error": str(e)
                }
                results.append(error_result)
                print(f"❌ Group {group_index} failed: {e}")
    
    return results


def main():
    """
    主函数，支持命令行参数
    """
    parser = argparse.ArgumentParser(description='Convert JSONL to experiences using experience maker service')
    parser.add_argument('--jsonl_file', type=str, required=True, help='Path to the JSONL file')
    parser.add_argument('--service_url', type=str, default='http://localhost:8001', help='Experience maker service URL')
    parser.add_argument('--workspace_id', type=str, required=True, help='Workspace ID for the experience')
    parser.add_argument('--output_file', type=str, help='Output file to save results (optional)')
    parser.add_argument('--n_threads', type=int, default=4, help='Number of threads for processing')
    
    args = parser.parse_args()
    
    print(f"Processing JSONL file: {args.jsonl_file}")
    print(f"Service URL: {args.service_url}")
    print(f"Workspace ID: {args.workspace_id}")
    print(f"Threads: {args.n_threads}")
    
    # 读取JSONL文件
    try:
        with open(args.jsonl_file, "r") as f:
            data = [json.loads(line) for line in f]
        print(f"Loaded {len(data)} entries from JSONL file")
    except Exception as e:
        print(f"Error reading JSONL file: {e}")
        return
    
    # 分组处理
    grouped_trajectories = group_trajectories_by_task_id(data)
    print(f"Total groups: {len(grouped_trajectories)}")
    
    # 多线程处理
    results = process_trajectories_with_threads(
        grouped_trajectories, 
        args.service_url, 
        args.workspace_id,
        n_threads=args.n_threads
    )
    
    print(f"Processed {len(results)} groups")
    
    # 统计结果
    success_count = sum(1 for r in results if 'error' not in r)
    error_count = len(results) - success_count
    total_experiences = sum(len(r.get('experiences', [])) for r in results if 'experiences' in r)

    
    print(f"✅ Success: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total experiences created: {total_experiences}")
    
    # 保存结果到文件
    if args.output_file:
        try:
            summary = {
                "workspace_id": args.workspace_id,
                "jsonl_file": args.jsonl_file,
                "total_groups": len(grouped_trajectories),
                "success_count": success_count,
                "error_count": error_count,
                "total_experiences": total_experiences,
                "results": results
            }
            
            with open(args.output_file, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"Results saved to: {args.output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")


# 保持原有的使用示例（向后兼容）
if __name__ == "__main__":
    # 检查是否有命令行参数
    import sys
    if len(sys.argv) > 1:
        # 使用新的命令行接口
        main()
    else:
        # 保持原有的行为（向后兼容）
        print("Running in compatibility mode...")
        with open("exp_result/bfcl-multi-turn-train50_wo-exp-w-think-mix-8b&14b&32b.jsonl", "r") as f:
            data = [json.loads(line) for line in f]
        
        # 分组
        grouped_trajectories = group_trajectories_by_task_id(data)
        print(f"Total groups: {len(grouped_trajectories)}")
        
        results = process_trajectories_with_threads(
            grouped_trajectories, 
            "http://localhost:8003", 
            "bfcl_train50_qwen3_mix_32b&8b&14b_extract_compare_validate_categorized-noshuffle",
            n_threads=4
        )
        print(f"Processed {len(results)} groups")