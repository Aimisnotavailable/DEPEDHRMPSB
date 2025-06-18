# ANSI color codes
RESET = "\033[0m"
LOG_COLORS = {
    "ERROR": "\033[31m",  # Red
    "APP"  : "\033[33m",  # Yellow
    "CORE" : "\033[34m",  # Blue
}

def get_log_info(log_type="ERROR", msg="ERROR FAULT AT THIS METHOD", func_name="MAIN"):
    color = LOG_COLORS.get(log_type.upper(), "")
    # pad to 5 chars (e.g. [ERROR], [CORE ], [APP  ])
    label = f"[{log_type:<5}]"
    print(f"{color}{label} {msg} ({func_name}){RESET}")