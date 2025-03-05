import uvicorn
import argparse
import os
import socket
import subprocess
import signal
import sys
import atexit
import time
import shutil
import glob

def is_port_available(port):
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except:
            return False

def find_available_port(start_port):
    """Find an available port starting from start_port."""
    current_port = start_port
    while not is_port_available(current_port):
        print(f"Port {current_port} is in use, trying next port...")
        current_port += 1
    return current_port

def start_streamlit(data_dir, port=8501):
    """Start the Streamlit dashboard."""
    streamlit_port = find_available_port(port)
    print(f"Starting Streamlit dashboard on port {streamlit_port}...")
    
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard/streamlit_app.py", 
         "--server.port", str(streamlit_port), "--server.headless", "true"],
        env=dict(os.environ, DATA_DIR=data_dir)
    )
    print(f"Streamlit dashboard starting at http://localhost:{streamlit_port}")
    print(f"Streamlit PID: {streamlit_process.pid}")
    return streamlit_process

def cleanup(processes):
    """Clean up processes on exit."""
    for process in processes:
        if process:
            print(f"Terminating process {process.pid}")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

def cleanup_environment():
    """Clean up environment before starting."""
    # Kill existing processes
    print("Cleaning up existing processes...")
    try:
        subprocess.run(["pkill", "-f", "uvicorn backend.main:app"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "streamlit run dashboard/streamlit_app.py"], stderr=subprocess.DEVNULL)
    except:
        pass
    
    # Remove backend.pid if it exists
    if os.path.exists("backend.pid"):
        with open("backend.pid", "r") as f:
            try:
                pid = int(f.read().strip())
                try:
                    os.kill(pid, signal.SIGTERM)
                except:
                    pass
            except:
                pass
        os.remove("backend.pid")

    # Check for database lock
    print("Ensuring database is not locked...")
    db_lock = "data/spotify_streaming.duckdb.lock"
    if os.path.exists(db_lock):
        print(f"Removing stale database lock file: {db_lock}")
        os.remove(db_lock)
    
    # Clean Python cache files
    print("Cleaning Python cache files...")
    for pycache in glob.glob("**/__pycache__", recursive=True):
        try:
            shutil.rmtree(pycache)
        except:
            pass
    
    for pyc in glob.glob("**/*.pyc", recursive=True):
        try:
            os.remove(pyc)
        except:
            pass

def initialize_db(force_reload=False, clear=False):
    """Initialize the database."""
    cmd = [sys.executable, "load_data.py"]
    if force_reload:
        cmd.append("--force-reload")
    if clear:
        cmd.append("--clear")
    
    print(f"Running database initialization: {' '.join(cmd)}")
    process = subprocess.run(cmd)
    
    if process.returncode != 0:
        print("Database initialization failed!")
        return False
    return True

def main():
    """Entry point for the application."""
    parser = argparse.ArgumentParser(description="Run the Spotify Streaming Journey application.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Backend port number")
    parser.add_argument("--streamlit-port", type=int, default=8501, help="Streamlit port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reloading for backend")
    parser.add_argument("--data-dir", type=str, default="data", help="Path to the data directory")
    parser.add_argument("--init-db", action="store_true", help="Initialize database before starting")
    parser.add_argument("--clear-db", action="store_true", help="Clear and reinitialize database")
    parser.add_argument("--no-streamlit", action="store_true", help="Don't start Streamlit dashboard")
    parser.add_argument("--no-backend", action="store_true", help="Don't start backend server")
    
    args = parser.parse_args()
    
    # Clean up environment first
    cleanup_environment()
    
    # Set environment variables
    os.environ["DATA_DIR"] = args.data_dir
    os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{os.getcwd()}"
    os.environ["METADATA_PARQUET_PATH"] = os.path.join(args.data_dir, "metadata/metadata.parquet")
    
    # Create directories if needed
    os.makedirs(os.path.join(args.data_dir, "metadata"), exist_ok=True)
    
    # Check if virtual environment is active
    if os.path.exists(".venv"):
        print("Virtual environment detected.")
    
    # Initialize database if requested
    if args.init_db:
        if not initialize_db(force_reload=True):
            sys.exit(1)
    elif args.clear_db:
        if not initialize_db(force_reload=True, clear=True):
            sys.exit(1)
    
    processes = []
    
    # Start the backend server if not disabled
    if not args.no_backend:
        backend_port = find_available_port(args.port)
        print(f"Starting backend on port {backend_port}...")
        
        # Build the uvicorn command
        uvicorn_command = [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", args.host,
            "--port", str(backend_port)
        ]
        if args.reload:
            uvicorn_command.append("--reload")
        
        # Start the backend
        api_process = subprocess.Popen(uvicorn_command)
        processes.append(api_process)
        
        # Save PID to file
        with open("backend.pid", "w") as f:
            f.write(str(api_process.pid))
        
        print(f"API server starting at http://localhost:{backend_port}")
        print(f"Backend PID: {api_process.pid}")
        
        # Give FastAPI a moment to start
        time.sleep(2)
        
        # Check if backend started properly
        if api_process.poll() is not None:
            print("Backend failed to start! Check the logs above for details.")
            cleanup(processes)
            sys.exit(1)
    
    # Start Streamlit if not disabled
    if not args.no_streamlit:
        streamlit_process = start_streamlit(args.data_dir, args.streamlit_port)
        processes.append(streamlit_process)
    
    # Register cleanup handler
    atexit.register(cleanup, processes)
    
    # Wait for processes to complete or interrupt
    try:
        # Wait for processes
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cleanup(processes)

if __name__ == "__main__":
    main()
