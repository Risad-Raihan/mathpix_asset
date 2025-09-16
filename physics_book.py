"""
Extract PDF to JSON format with Mathpix API and download images
• Saves `.json` output alongside the source PDF
• Downloads any extracted images into a folder named `<pdf-stem>_assets/`
• Preserves all structural data, coordinates, confidence scores
• Requires: pip install mpxpy >= 0.4.0
"""
from pathlib import Path
import json
import re
import requests
from mpxpy.mathpix_client import MathpixClient

# ---------- 1. AUTHENTICATION ----------
# Your Mathpix API credentials
APP_ID = "ztriostechnologiesltd__5927b4_af5e59"  # Replace with your actual APP ID
APP_KEY = "d8274e627562f11a6ee3210c6db5d538495617e845eaacc99de03b44156df96b"  # Replace with your actual API KEY

client = MathpixClient(app_id=APP_ID, app_key=APP_KEY)

# ---------- 2. CONFIG ----------
# path to the PDF you want to convert
PDF_PATH = Path("/home/risad/projects/mathpix_test/physics_class9_fullbook.pdf")

# where to put the resulting JSON
OUTPUT_DIR = PDF_PATH.parent
TIMEOUT_SEC = 300  # 5 minutes should be enough for 1 page

# Define assets directory
ASSETS_DIR = OUTPUT_DIR / f"{PDF_PATH.stem}_assets"

# ---------- 3. PROCESS PDF ----------
try:
    print(f"📄 Starting processing of {PDF_PATH.name}")
    print("⏳ Processing single page PDF...")
    
    pdf_job = client.pdf_new(
        file_path=str(PDF_PATH),  # local file
        convert_to_md=False,  # We want JSON, not markdown
    )
    
    print(f"🔄 PDF job created. Waiting for completion...")
    pdf_job.wait_until_complete(timeout=TIMEOUT_SEC)
    print("✅ PDF processing completed successfully")
    
except Exception as e:
    print(f"❌ Error processing PDF: {e}")
    exit(1)

# ---------- 4. SAVE JSON ----------
json_path = OUTPUT_DIR / f"{PDF_PATH.stem}.json"

# Get the JSON data using available methods
try:
    # Try the json_result attribute first
    if hasattr(pdf_job, 'json_result') and pdf_job.json_result:
        json_data = pdf_job.json_result
        print("✅ Using json_result attribute")
    elif hasattr(pdf_job, 'to_lines_json'):
        json_data = pdf_job.to_lines_json()
        print("✅ Using to_lines_json method")
    elif hasattr(pdf_job, 'to_lines_mmd_json'):
        json_data = pdf_job.to_lines_mmd_json()
        print("✅ Using to_lines_mmd_json method")
    else:
        raise AttributeError("No JSON method found")
    
    # Save JSON with proper formatting
    if isinstance(json_data, str):
        # If it's already a JSON string, parse it first
        json_data = json.loads(json_data)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON saved → {json_path}")
    
except Exception as e:
    print(f"❌ Error with JSON methods: {e}")
    print("🔄 Trying to_lines_json_file method...")
    try:
        # Try saving directly to file
        pdf_job.to_lines_json_file(str(json_path))
        print(f"✅ JSON saved directly → {json_path}")
        
        # Load it back to get the data for image extraction
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            
    except Exception as e2:
        print(f"❌ All JSON methods failed: {e2}")
        exit(1)

# ---------- 5. EXTRACT AND DOWNLOAD IMAGES ----------
def extract_images_from_json(json_data, assets_dir):
    """Extract image URLs from JSON data and download them"""
    # Create assets directory
    assets_dir.mkdir(exist_ok=True)
    
    downloaded_count = 0
    image_urls = set()  # Use set to avoid duplicates
    
    def find_images_recursive(obj):
        """Recursively find image URLs in JSON structure"""
        if isinstance(obj, dict):
            # Look for any field containing mathpix CDN URLs
            for key, value in obj.items():
                if isinstance(value, str):
                    # Extract URLs from markdown image format: ![](URL)
                    if '![](https://cdn.mathpix.com' in value:
                        # Extract URL from markdown format
                        import re
                        urls = re.findall(r'!\[\]\((https://cdn\.mathpix\.com[^)]+)\)', value)
                        for url in urls:
                            image_urls.add(url)
                    # Also check for plain URLs
                    elif 'cdn.mathpix.com' in value:
                        image_urls.add(value)
                elif isinstance(value, (dict, list)):
                    find_images_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                find_images_recursive(item)
        elif isinstance(obj, str):
            # Handle strings that might contain markdown images
            if '![](https://cdn.mathpix.com' in obj:
                import re
                urls = re.findall(r'!\[\]\((https://cdn\.mathpix\.com[^)]+)\)', obj)
                for url in urls:
                    image_urls.add(url)
            elif 'cdn.mathpix.com' in obj:
                image_urls.add(obj)
    
    # Search for images in the JSON
    print("🔍 Scanning JSON for Mathpix CDN URLs...")
    find_images_recursive(json_data)
    
    print(f"📋 Found {len(image_urls)} unique image URLs")
    
    # Download each unique image
    for i, url in enumerate(image_urls, 1):
        try:
            # Extract filename from URL - use the cropped filename part
            url_path = url.split('?')[0]  # Remove query parameters for filename
            base_filename = url_path.split('/')[-1]  # Get the last part
            
            # Add crop parameters to make filename unique
            if '?' in url:
                # Extract crop info to make unique filenames
                query_params = url.split('?')[1]
                # Create a hash from the parameters to ensure uniqueness
                import hashlib
                param_hash = hashlib.md5(query_params.encode()).hexdigest()[:8]
                
                name_part = base_filename.split('.')[0]
                ext_part = base_filename.split('.')[-1] if '.' in base_filename else 'jpg'
                filename = f"{name_part}_crop_{param_hash}.{ext_part}"
            else:
                filename = base_filename
            
            if not filename or '.' not in filename:
                filename = f"mathpix_image_{i}.jpg"
            
            print(f"📥 [{i}/{len(image_urls)}] Downloading: {filename}")
            print(f"🔗 URL: {url}")
            
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Save to assets directory
            asset_path = assets_dir / filename
            asset_path.write_bytes(response.content)
            downloaded_count += 1
            print(f"✅ Saved: {filename} ({len(response.content)} bytes)")
            
        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")
    
    return downloaded_count

# Download images from the JSON data
print(f"\n📥 Searching for images in JSON data...")
dl_count = extract_images_from_json(json_data, ASSETS_DIR)

if dl_count > 0:
    print(f"✅ {dl_count} image(s) saved → {ASSETS_DIR}")
else:
    print("ℹ️  No images found in the JSON data")

# ---------- 6. SUMMARY ----------
print(f"\n📊 Processing Summary:")
print(f"   📄 Source: {PDF_PATH.name}")
print(f"   📝 JSON: {json_path.name}")
print(f"   🖼️  Images: {dl_count}")
print(f"   📁 Assets folder: {ASSETS_DIR.name}")

print("\n✅ JSON extraction completed successfully!")