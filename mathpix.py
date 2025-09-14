"""
Convert an entire PDF to Markdown with Mathpix Markdown (MMD) via
Mathpix's official Python SDK (mpxpy).
• Saves `.md` output alongside the source PDF
• Wraps every inline or display equation in $ … $ (handled automatically
by Mathpix)
• Downloads any extracted diagram/table images into a folder named
`<pdf-stem>_assets/`
• Requires: pip install mpxpy >= 0.4.0
"""
from pathlib import Path
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
PDF_PATH = Path("/home/risad/projects/mathpix_test/general_math_ssc_split.pdf")

# where to put the resulting markdown
OUTPUT_DIR = PDF_PATH.parent
TIMEOUT_SEC = 300  # increased timeout for large PDFs

# Define assets directory
ASSETS_DIR = OUTPUT_DIR / f"{PDF_PATH.stem}_assets"

# ---------- 3. PROCESS PDF ----------
try:
    pdf_job = client.pdf_new(
        file_path=str(PDF_PATH),  # local file; or use url=... for remote
        convert_to_md=True,  # keep diagrams/tables as separate assets
    )
    pdf_job.wait_until_complete(timeout=TIMEOUT_SEC)
    print("PDF processing completed successfully")
    
except Exception as e:
    print(f"Error processing PDF: {e}")
    exit(1)

# ---------- 4. SAVE MARKDOWN ----------
md_path = OUTPUT_DIR / f"{PDF_PATH.stem}.md"
md_text = pdf_job.to_md_text()
md_path.write_text(md_text, encoding="utf-8")
print(f"Markdown saved → {md_path}")

# ---------- 5. DOWNLOAD ASSETS ----------
def download_assets_from_markdown(md_text, assets_dir):
    """Extract image URLs from markdown and download them"""
    # Create assets directory
    assets_dir.mkdir(exist_ok=True)
    
    # Find all image references in the markdown
    image_patterns = [
        r'!\[.*?\]\((https://cdn\.mathpix\.com/[^)]+)\)',  # Standard markdown images
        r'<img[^>]+src="(https://cdn\.mathpix\.com/[^"]+)"[^>]*>',  # HTML img tags
    ]
    
    downloaded_count = 0
    all_urls = []
    
    # Collect all URLs
    for pattern in image_patterns:
        urls = re.findall(pattern, md_text)
        all_urls.extend(urls)
    
    # Remove duplicates while preserving order
    unique_urls = list(dict.fromkeys(all_urls))
    
    for url in unique_urls:
        try:
            # Extract filename from URL
            filename = url.split('/')[-1].split('?')[0]  # Remove query parameters
            if not filename or '.' not in filename:
                filename = f"image_{downloaded_count}.png"
            
            # Download the image
            print(f"Downloading: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Save to assets directory
            asset_path = assets_dir / filename
            asset_path.write_bytes(response.content)
            downloaded_count += 1
            print(f"✅ Downloaded: {filename}")
            
        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")
    
    return downloaded_count

# Download assets from the markdown content
print(f"\n📥 Starting asset download to: {ASSETS_DIR}")
dl_count = download_assets_from_markdown(md_text, ASSETS_DIR)
print(f"✅ {dl_count} asset(s) saved → {ASSETS_DIR}")

# ---------- 6. DONE ----------
print("\n✅ Conversion finished successfully!")