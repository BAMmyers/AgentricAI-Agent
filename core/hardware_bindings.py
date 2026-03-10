"""
AgentricAI Hardware Bindings.
Provides hardware detection and execution mode binding.
"""
from datetime import datetime
import os
import platform
from typing import Dict, Any, Optional, List

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

try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False


class HardwareDetector:
    """
    Detects and manages hardware capabilities.
    
    Features:
    - GPU detection via NVML/GPUtil
    - CPU detection with frequency and cores
    - Memory detection
    - Storage detection
    - Execution mode recommendations
    """
    
    def __init__(self):
        """Initialize hardware detector."""
        self._gpu_info: Optional[List[Dict]] = None
        self._cpu_info: Optional[Dict] = None
        self._memory_info: Optional[Dict] = None
        self._initialized_nvml = False
        
        # Try to initialize NVML
        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self._initialized_nvml = True
            except Exception:
                pass
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """
        Get GPU information using available methods.
        
        Returns:
            Dictionary with GPU information
        """
        if self._gpu_info is not None:
            return self._gpu_info
        
        gpus = []
        
        # Try NVML first (most reliable for NVIDIA)
        if self._initialized_nvml:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    
                    try:
                        memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        memory_total = memory_info.total / (1024**3)
                    except Exception:
                        memory_total = 0
                    
                    try:
                        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                        gpu_util = util.gpu
                        memory_util = util.memory
                    except Exception:
                        gpu_util = 0
                        memory_util = 0
                    
                    gpus.append({
                        'name': name,
                        'memory_gb': round(memory_total, 2),
                        'utilization': gpu_util,
                        'memory_utilization': memory_util,
                        'index': i
                    })
            except Exception as e:
                pass
        
        # Fallback to GPUtil
        if not gpus and GPUTIL_AVAILABLE:
            try:
                gpu_list = GPUtil.getGPUs()
                for gpu in gpu_list:
                    gpus.append({
                        'name': gpu.name,
                        'memory_gb': round(gpu.memoryTotal / 1024, 2),
                        'utilization': gpu.load * 100,
                        'memory_utilization': gpu.memoryUtil * 100,
                        'index': gpu.id
                    })
            except Exception:
                pass
        
        # If no GPUs found, return empty but valid structure
        if not gpus:
            self._gpu_info = {
                'available': False,
                'count': 0,
                'devices': [],
                'message': 'No GPU detected or drivers not installed'
            }
        else:
            self._gpu_info = {
                'available': True,
                'count': len(gpus),
                'devices': gpus
            }
        
        return self._gpu_info
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """
        Get CPU information.
        
        Returns:
            Dictionary with CPU information
        """
        if self._cpu_info is not None:
            return self._cpu_info
        
        info = {
            'processor': platform.processor() or 'Unknown',
            'cores_physical': 1,
            'cores_logical': 1,
            'frequency_mhz': 0,
            'usage_percent': 0
        }
        
        if PSUTIL_AVAILABLE:
            info['cores_physical'] = psutil.cpu_count(logical=False) or 1
            info['cores_logical'] = psutil.cpu_count(logical=True) or 1
            
            freq = psutil.cpu_freq()
            if freq:
                info['frequency_mhz'] = round(freq.current, 0)
                info['frequency_max_mhz'] = round(freq.max, 0) if freq.max else 0
            
            info['usage_percent'] = psutil.cpu_percent(interval=0.1)
        
        self._cpu_info = info
        return info
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get memory (RAM) information.
        
        Returns:
            Dictionary with memory information
        """
        if self._memory_info is not None:
            return self._memory_info
        
        info = {
            'total_gb': 0,
            'available_gb': 0,
            'used_gb': 0,
            'usage_percent': 0
        }
        
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            info['total_gb'] = round(mem.total / (1024**3), 2)
            info['available_gb'] = round(mem.available / (1024**3), 2)
            info['used_gb'] = round(mem.used / (1024**3), 2)
            info['usage_percent'] = mem.percent
        
        self._memory_info = info
        return info
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information.
        
        Returns:
            Dictionary with storage information
        """
        info = {
            'total_gb': 0,
            'used_gb': 0,
            'free_gb': 0,
            'usage_percent': 0
        }
        
        if PSUTIL_AVAILABLE:
            # Use appropriate root for OS
            root = 'C:\\' if platform.system() == 'Windows' else '/'
            try:
                disk = psutil.disk_usage(root)
                info['total_gb'] = round(disk.total / (1024**3), 2)
                info['used_gb'] = round(disk.used / (1024**3), 2)
                info['free_gb'] = round(disk.free / (1024**3), 2)
                info['usage_percent'] = disk.percent
            except Exception:
                pass
        
        return info
    
    def get_recommended_execution_mode(self) -> str:
        """
        Get recommended execution mode based on hardware.
        
        Returns:
            'GPU', 'CPU', or 'Mixed'
        """
        gpu_info = self.get_gpu_info()
        cpu_info = self.get_cpu_info()
        
        if gpu_info.get('available') and gpu_info.get('count', 0) > 0:
            # Check GPU memory - need at least 4GB for GPU execution
            for device in gpu_info.get('devices', []):
                if device.get('memory_gb', 0) >= 4:
                    return 'GPU'
            return 'Mixed'
        
        if cpu_info.get('cores_logical', 1) >= 8:
            return 'CPU'
        
        return 'Mixed'
    
    def get_system_summary(self) -> Dict[str, Any]:
        """
        Get complete system summary.
        
        Returns:
            Dictionary with all hardware information
        """
        return {
            'gpu': self.get_gpu_info(),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'storage': self.get_storage_info(),
            'recommended_mode': self.get_recommended_execution_mode(),
            'platform': platform.system(),
            'platform_version': platform.version()
        }
    
    def __del__(self):
        """Cleanup NVML on destruction."""
        if self._initialized_nvml:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass


# Global detector instance
_detector: Optional[HardwareDetector] = None


def get_hardware_detector() -> HardwareDetector:
    """Get the global hardware detector instance."""
    global _detector
    if _detector is None:
        _detector = HardwareDetector()
    return _detector


# Convenience functions for backward compatibility
def get_gpu_info() -> str:
    """Get GPU information as string (backward compatible)."""
    detector = get_hardware_detector()
    info = detector.get_gpu_info()
    
    if not info.get('available'):
        return "No GPU detected"
    
    devices = info.get('devices', [])
    if devices:
        return devices[0].get('name', 'Unknown GPU')
    
    return "No GPU detected"


def get_cpu_info() -> str:
    """Get CPU information as string (backward compatible)."""
    detector = get_hardware_detector()
    info = detector.get_cpu_info()
    
    freq_str = f" • {info['frequency_mhz']:.0f} MHz" if info.get('frequency_mhz') else ""
    return f"{info['processor']}{freq_str}"


def get_ram_info() -> str:
    """Get RAM information as string (backward compatible)."""
    detector = get_hardware_detector()
    info = detector.get_memory_info()
    return f"{info['total_gb']:.2f} GB"


def get_memory_size() -> str:
    """Alias for get_ram_info."""
    return get_ram_info()


def bind_agent_execution_mode(agent_id: str, use_gpu: bool = False) -> str:
    """
    Bind an agent to an execution mode.
    
    Args:
        agent_id: The agent identifier
        use_gpu: Whether to prefer GPU execution
        
    Returns:
        Status message
    """
    detector = get_hardware_detector()
    
    if use_gpu:
        gpu_info = detector.get_gpu_info()
        if gpu_info.get('available'):
            mode = "GPU"
        else:
            mode = "CPU (GPU requested but not available)"
    else:
        mode = detector.get_recommended_execution_mode()
    
    return f"Agent {agent_id} bound to {mode} execution mode"


def log_operation(agent_id: str, action: str, details: str) -> None:
    """
    Log an operation with timestamp.
    
    Args:
        agent_id: The agent identifier
        action: The action performed
        details: Operation details
    """
    from core.logging_config import get_logger
    logger = get_logger(f"agent.{agent_id}")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Operation: {action} - {details}")
    
    # Also write to audit log file
    try:
        audit_path = os.path.join(os.path.dirname(__file__), '..', 'audit_log.txt')
        with open(audit_path, "a", encoding='utf-8') as file:
            file.write(f"{timestamp} - Agent {agent_id}: {action} - {details}\n")
    except Exception:
        pass


if __name__ == "__main__":
    # Demo usage
    detector = get_hardware_detector()
    summary = detector.get_system_summary()
    
    print("=== Hardware Summary ===")
    print(f"Platform: {summary['platform']}")
    print(f"Recommended Mode: {summary['recommended_mode']}")
    print()
    
    print("GPU Info:")
    gpu = summary['gpu']
    if gpu['available']:
        for device in gpu['devices']:
            print(f"  - {device['name']} ({device['memory_gb']} GB)")
    else:
        print(f"  {gpu['message']}")
    
    print()
    print(f"CPU: {summary['cpu']['processor']}")
    print(f"  Cores: {summary['cpu']['cores_physical']} physical, {summary['cpu']['cores_logical']} logical")
    print(f"  Frequency: {summary['cpu']['frequency_mhz']} MHz")
    
    print()
    print(f"Memory: {summary['memory']['total_gb']} GB")
    print(f"Storage: {summary['storage']['total_gb']} GB")
