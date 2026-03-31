#!/usr/bin/env python3
"""Builds the browser extension into a zip file for easy distribution."""

import os
import zipfile
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

def build_extension():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    extension_dir = os.path.join(project_root, "browser_extension")
    dist_dir = os.path.join(project_root, "dist")
    
    if not os.path.exists(extension_dir):
        logging.error(f"Error: {extension_dir} does not exist.")
        return False
        
    os.makedirs(dist_dir, exist_ok=True)
    
    zip_path = os.path.join(dist_dir, "pydm_extension.zip")
    logging.info(f"Building extension package: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(extension_dir):
            # Ignore hidden files or directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, extension_dir)
                    zipf.write(full_path, rel_path)
                    
    logging.info("Extension built successfully! 🎉")
    return True

if __name__ == "__main__":
    build_extension()
