#!/usr/bin/env bash
set -e

# Support localized desktop translation mappings if "Escritorio" exists instead of "Desktop"
USER_DESKTOP=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")

echo -e "\e[1;36m==================================================\e[0m"
echo -e "\e[1;36m             PyDM - Download Manager\e[0m"
echo -e "\e[1;36m               Production Installer\e[0m"
echo -e "\e[1;36m==================================================\e[0m"

INSTALL_DIR="$HOME/.local/share/pydm"
DESKTOP_ZIP="$USER_DESKTOP/pydm_extension.zip"
IS_UPDATE=false

if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/pydm/main.py" ]; then
    IS_UPDATE=true
    echo -e "\e[1;36m               (Update Mode Detected)\e[0m"
fi
echo -e "\e[1;36m==================================================\e[0m"

if [ "$IS_UPDATE" = false ]; then
    echo -e "\n\e[1;34m[1/5] Checking system dependencies...\e[0m"
    if command -v apt-get >/dev/null; then
        echo "Ubuntu/Debian detected. Asking for permission to install aria2, ffmpeg, python3-venv..."
        sudo apt-get update && sudo apt-get install -y aria2 ffmpeg python3-venv python3-pip xdg-utils
    elif command -v pacman >/dev/null; then
        echo "Arch Linux detected. Asking for permission to install aria2, ffmpeg, python..."
        sudo pacman -S --needed --noconfirm aria2 ffmpeg python xdg-utils
    elif command -v dnf >/dev/null; then
        echo "Fedora detected. Asking for permission to install aria2, ffmpeg..."
        sudo dnf install -y aria2 ffmpeg python3 xdg-utils
    else
        echo -e "\e[1;33mWarning: Package manager not found. Please manually ensure aria2, ffmpeg, and python3-venv are installed.\e[0m"
    fi
else
    echo -e "\n\e[1;34m[1/5] Skipping system dependencies (Update Mode)...\e[0m"
fi

echo -e "\n\e[1;34m[2/5] Deploying PyDM to $INSTALL_DIR...\e[0m"
mkdir -p "$INSTALL_DIR"
if [ -f "./pydm/main.py" ]; then
    echo "Copying local files..."
    cp -r ./* "$INSTALL_DIR"/
else
    echo "Fetching from Git repository..."
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR" && git pull origin main && cd -
    else
        git clone https://github.com/happy-fox-devs/pydm.git "$INSTALL_DIR"
    fi
fi

echo -e "\n\e[1;34m[3/5] Setting up isolated Python environment...\e[0m"
cd "$INSTALL_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

echo -e "\n\e[1;34m[4/5] Registering Browser Native Messaging & Desktop Icon...\e[0m"
chmod +x native_host/install.sh
bash native_host/install.sh --chrome --firefox

echo -e "\n\e[1;34m[5/5] Packaging Browser Extension...\e[0m"
python3 scripts/build_extension.py
if [ -d "$USER_DESKTOP" ] && [ -f "dist/pydm_extension.zip" ]; then
    cp dist/pydm_extension.zip "$DESKTOP_ZIP"
    EXT_LOCATION="$DESKTOP_ZIP"
else
    EXT_LOCATION="$INSTALL_DIR/dist/pydm_extension.zip"
fi

echo -e "\n\e[1;32m==================================================\e[0m"
if [ "$IS_UPDATE" = true ]; then
    echo -e "\e[1;32m       PyDM Updated Successfully! 🎉\e[0m"
else
    echo -e "\e[1;32m       PyDM Installed Successfully! 🎉\e[0m"
fi
echo -e "\e[1;32m==================================================\e[0m"
echo -e "\e[1;37m"
echo "> PyDM has been installed to your local user directory."
echo "> The Desktop shortcut was added to your App Launcher (Search 'PyDM')."
echo ""
echo -e "\e[1;33mFinal Step for Browser Integration:\e[0m"
echo "1. Your extension package has been dropped here:"
echo "   -> $EXT_LOCATION"
echo "2. Open chrome://extensions (or brave://extensions)"
echo "3. Turn ON 'Developer mode' (Top right)"
echo "4. Drag and drop the .zip file directly into the browser."
echo -e "\e[0m"

# Try to open the extension guide logically
if command -v xdg-open >/dev/null; then
    echo "Attempting to open default browser..."
    xdg-open "https://chrome.google.com/webstore/category/extensions" || true
fi
