import os
import zipfile
from pathlib import Path

def create_lambda_zip():
    """Create Lambda deployment package with correct structure"""
    
    source_dir = Path("lambda_deployment_package")
    output_zip = Path("lambda-function.zip")
    
    # Remove old zip if exists
    if output_zip.exists():
        output_zip.unlink()
        print(f"Removed old {output_zip}")
    
    print(f"Creating Lambda deployment package from {source_dir}...")
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files in source directory
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                # Calculate relative path from source_dir
                arcname = file_path.relative_to(source_dir)
                zipf.write(file_path, arcname)
                if len(files) < 10:  # Print first few files
                    print(f"  Added: {arcname}")
    
    # Verify the zip
    print(f"\nVerifying {output_zip}...")
    with zipfile.ZipFile(output_zip, 'r') as zipf:
        all_files = zipf.namelist()
        
        # Check for app.py at root
        if 'app.py' in all_files:
            print("  ✓ app.py found at root")
        else:
            print("  ✗ ERROR: app.py not at root!")
        
        # Check for requests module
        requests_files = [f for f in all_files if f.startswith('requests/')]
        if requests_files:
            print(f"  ✓ requests module found ({len(requests_files)} files)")
        else:
            print("  ✗ ERROR: requests module not found!")
        
        # Check for other dependencies
        for module in ['urllib3', 'certifi', 'idna', 'charset_normalizer']:
            module_files = [f for f in all_files if f.startswith(f'{module}/')]
            if module_files:
                print(f"  ✓ {module} module found")
        
        print(f"\n  Total files: {len(all_files)}")
        print(f"  Zip size: {output_zip.stat().st_size / (1024*1024):.2f} MB")
    
    print(f"\n✓ Successfully created {output_zip}")
    print("\nReady to upload to AWS Lambda!")

if __name__ == "__main__":
    create_lambda_zip()
