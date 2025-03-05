import os
import shutil
import subprocess
import sys

def clean_cache():
    """Remove all __pycache__ directories and .pyc files"""
    # Remove __pycache__ directories
    for root, dirs, files in os.walk('.'):
        for dir in dirs:
            if dir == '__pycache__':
                path = os.path.join(root, dir)
                print(f'Removing cache directory: {path}')
                shutil.rmtree(path)
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                path = os.path.join(root, file)
                print(f'Removing cache file: {path}')
                os.remove(path)

def run_bot():
    """Run the bot with python"""
    python_executable = sys.executable
    try:
        subprocess.run([python_executable, 'src/bot.py'], check=True)
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"Bot crashed with exit code {e.returncode}")

if __name__ == "__main__":
    clean_cache()
    run_bot()