import warnings
import sys

def suppress_process_pool_errors():
    """
    Suppress the 'NoneType' object has no attribute 'util' error that occurs 
    during shutdown of ProcessPoolExecutor.
    
    This is a harmless error that happens during interpreter shutdown when
    process pools are still active. It's related to Python's concurrent.futures
    module and occurs in the weakref callback when Python is shutting down.
    
    The error can be safely ignored as it doesn't affect program execution.
    """
    # Suppress warnings about process pool
    warnings.filterwarnings("ignore", message=".*AttributeError: 'NoneType' object has no attribute 'util'.*")
    
    # Redirect stderr to filter out the specific error
    original_stderr = sys.stderr
    
    class StderrFilter:
        def write(self, message):
            if "AttributeError: 'NoneType' object has no attribute 'util'" not in message:
                original_stderr.write(message)
        def flush(self):
            original_stderr.flush()
    
    sys.stderr = StderrFilter()