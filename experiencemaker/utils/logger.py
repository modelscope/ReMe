from best_logger import register_logger

def init_logger():
    register_logger(
        mods=["agent", "context", "summary"], 
        non_console_mods=[], 
        auto_clean_mods=[],
        base_log_path=f"logs/default"
    )


