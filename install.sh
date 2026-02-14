#!/bin/bash

# Configuration
REPO_URL="https://github.com/basil-saji/bcli.git"
INSTALL_DIR="$HOME/.bcli"

echo "Installing bcli..."

# 1. Clone the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory exists. Updating..."
    cd "$INSTALL_DIR" && git pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 2. Setup Virtual Environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create Alias
if ! grep -q "alias bcli=" ~/.bashrc; then
    echo "alias bcli='source $INSTALL_DIR/venv/bin/activate && python3 $INSTALL_DIR/main.py'" >> ~/.bashrc
    echo "Alias added to .bashrc. Run 'source ~/.bashrc' or restart terminal to use 'bcli'."
fi

echo "Successfully installed! Type 'bcli' to start."