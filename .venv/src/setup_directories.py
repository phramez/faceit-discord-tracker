import os

def create_project_structure():
    # List of directories to create
    directories = [
        'src',
        'src/cogs',
        'src/services',
        'src/utils'
    ]
    
    # Create each directory
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        # Create __init__.py in each directory
        with open(os.path.join(directory, '__init__.py'), 'a'):
            pass

    print("Project structure created successfully!")

if __name__ == "__main__":
    create_project_structure()