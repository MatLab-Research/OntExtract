#!/usr/bin/env python3
"""
Script to generate and optionally crop PROV-O visualization for paper inclusion.
Uses Selenium for automated screenshot capture and ImageMagick for cropping.
"""

import os
import time
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required tools are installed."""
    try:
        subprocess.run(['convert', '--version'], capture_output=True, check=True)
        print("✓ ImageMagick is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ ImageMagick is not installed. Please install it:")
        print("  Ubuntu/Debian: sudo apt-get install imagemagick")
        print("  macOS: brew install imagemagick")
        return False
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        print("✓ Selenium is installed")
    except ImportError:
        print("✗ Selenium is not installed. Please install it:")
        print("  pip install selenium")
        return False
    
    return True

def capture_visualization(url="http://localhost:8765/provenance/graph/compact", 
                         output_path="prov_o_figure.png"):
    """Capture the visualization using Selenium."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=800,600")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print(f"Loading visualization from {url}...")
        driver.get(url)
        
        # Wait for the graph to render
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "cy"))
        )
        time.sleep(2)  # Extra time for graph layout
        
        # Take screenshot
        driver.save_screenshot(output_path)
        print(f"✓ Screenshot saved to {output_path}")
        
        driver.quit()
        return True
    except Exception as e:
        print(f"✗ Error capturing visualization: {e}")
        return False

def crop_for_paper(input_path="prov_o_figure.png", 
                   output_path="prov_o_figure_cropped.png",
                   crop_mode="graph_and_legend"):
    """
    Crop the image for paper inclusion using ImageMagick.
    
    Crop modes:
    - 'graph_only': Just the graph visualization
    - 'graph_and_legend': Graph plus legend (recommended)
    - 'custom': Custom crop with specified dimensions
    """
    
    if not Path(input_path).exists():
        print(f"✗ Input file {input_path} does not exist")
        return False
    
    try:
        if crop_mode == "graph_only":
            # Crop to just the graph area (approximate dimensions)
            cmd = [
                'convert', input_path,
                '-crop', '600x400+100+50',  # width x height + x_offset + y_offset
                '+repage',
                output_path
            ]
        elif crop_mode == "graph_and_legend":
            # Crop to include graph and legend
            cmd = [
                'convert', input_path,
                '-crop', '600x520+100+50',  # Includes graph and legend
                '+repage',
                output_path
            ]
        else:  # custom
            # Use auto-crop to remove white borders
            cmd = [
                'convert', input_path,
                '-trim',
                '+repage',
                output_path
            ]
        
        subprocess.run(cmd, check=True)
        print(f"✓ Cropped image saved to {output_path}")
        
        # Optimize for paper (reduce file size while maintaining quality)
        optimize_cmd = [
            'convert', output_path,
            '-quality', '95',
            '-density', '300',  # High DPI for print
            output_path.replace('.png', '_optimized.png')
        ]
        subprocess.run(optimize_cmd, check=True)
        print(f"✓ Optimized image saved to {output_path.replace('.png', '_optimized.png')}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error cropping image: {e}")
        return False

def generate_multiple_versions():
    """Generate multiple versions for the user to choose from."""
    base_name = "prov_o_figure"
    
    # Different crop options
    crops = [
        ("graph_only", f"{base_name}_graph_only.png"),
        ("graph_and_legend", f"{base_name}_with_legend.png"),
        ("custom", f"{base_name}_auto_trimmed.png")
    ]
    
    for crop_mode, output_name in crops:
        print(f"\nGenerating {crop_mode} version...")
        crop_for_paper(
            input_path=f"{base_name}.png",
            output_path=output_name,
            crop_mode=crop_mode
        )

def main():
    """Main function to generate paper figure."""
    print("PROV-O Visualization Figure Generator for Papers")
    print("=" * 50)
    
    if not check_dependencies():
        print("\nPlease install missing dependencies and try again.")
        return
    
    # Check if OntExtract is running
    import requests
    try:
        response = requests.get("http://localhost:8765/provenance/graph/compact", timeout=2)
        if response.status_code != 200:
            print("✗ OntExtract server is not responding correctly")
            print("  Please start it with: cd OntExtract && python run.py")
            return
    except requests.exceptions.RequestException:
        print("✗ OntExtract server is not running")
        print("  Please start it with: cd OntExtract && python run.py")
        return
    
    print("\n✓ OntExtract server is running")
    
    # Capture the visualization
    if capture_visualization():
        print("\nGenerating cropped versions for paper...")
        generate_multiple_versions()
        
        print("\n" + "=" * 50)
        print("Figure generation complete!")
        print("\nGenerated files:")
        print("  - prov_o_figure.png (full screenshot)")
        print("  - prov_o_figure_graph_only.png (graph only)")
        print("  - prov_o_figure_with_legend.png (graph + legend)")
        print("  - prov_o_figure_auto_trimmed.png (auto-trimmed)")
        print("  - *_optimized.png versions (300 DPI for print)")
        print("\nChoose the version that best fits your paper's layout.")
        print("\nSuggested caption:")
        print('"Figure 2. PROV-O provenance graph showing document processing workflow."')

if __name__ == "__main__":
    main()
