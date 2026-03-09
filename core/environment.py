import platform

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False


def get_gpu_info():
    if GPUTIL_AVAILABLE:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    "vendor": getattr(gpu, 'vendor', 'NVIDIA'),
                    "model": gpu.name,
                    "core_count": getattr(gpu, 'cores', 0),
                    "memory_size": int(gpu.memoryTotal / 1024) if hasattr(gpu, 'memoryTotal') else 0
                }
        except Exception:
            pass
    return {
        "vendor": "Unknown",
        "model": "No GPU detected",
        "core_count": 0,
        "memory_size": 0
    }


def get_cpu_info():
    if PSUTIL_AVAILABLE:
        return {
            "model": platform.processor(),
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True)
        }
    return {
        "model": platform.processor(),
        "cores": 0,
        "threads": 0
    }


def get_memory_size():
    if PSUTIL_AVAILABLE:
        memory = psutil.virtual_memory()
        return int(memory.total / 1024**3)  # in GB
    return 0


def get_storage_info():
    if PSUTIL_AVAILABLE:
        storage = psutil.disk_partitions()
        total_space = sum(part.total for part in storage) / (1024**3)  # in GB
        used_space = sum(part.used for part in storage) / (1024**3)  # in GB
        free_space = total_space - used_space
        return {
            "total_space": int(total_space),
            "used_space": int(used_space),
            "free_space": int(free_space)
        }
    return {
        "total_space": 0,
        "used_space": 0,
        "free_space": 0
    }


def get_ram_info():
    """Get RAM information in GB."""
    if PSUTIL_AVAILABLE:
        memory = psutil.virtual_memory()
        return f"{memory.total / (1024**3):.2f} GB"
    return "Unknown"


def get_local_models():
    """Get list of local Ollama models."""
    import urllib.request
    import json
    
    models = []
    try:
        response = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5)
        data = json.loads(response.read().decode())
        for model in data.get("models", []):
            models.append({
                "name": model.get("name"),
                "size": model.get("size"),
                "modified": model.get("modified_at")
            })
    except Exception:
        pass
    return models
