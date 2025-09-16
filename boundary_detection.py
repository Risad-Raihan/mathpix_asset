import os
import json
import time
import google.generativeai as genai
from typing import List, Dict

class GeminiBoundaryDetector:
    def __init__(self, file_path: str, api_key: str):
        self.file_path = file_path
        self.content = self.load_file()
        
        # Configure Gemini
        genai.configure(api_key="AIzaSyCCjKJxOQjweJRirVUcoZqb2t8_qEIWOFQ") 
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Configure generation settings for better timeout handling
        self.generation_config = genai.types.GenerationConfig(
            max_output_tokens=8192,
            temperature=0.1,
        )
    
    def load_file(self) -> str:
        """Load the markdown file content"""
        with open(self.file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def chunk_content_by_size(self, max_chars: int = 3000) -> List[str]:
        """Split content into smaller chunks if too large"""
        if len(self.content) <= max_chars:
            return [self.content]
        
        # Split by sections or paragraphs
        sections = self.content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for section in sections:
            if len(current_chunk + section) > max_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = section
            else:
                current_chunk += "\n\n" + section if current_chunk else section
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def detect_boundaries_with_llm(self) -> List[str]:
        """Use Gemini to detect natural learning boundaries with retry logic"""
        
        # Check content size and split if necessary
        content_chunks = self.chunk_content_by_size()
        all_detected_chunks = []
        
        print(f"Processing {len(content_chunks)} content sections...")
        
        for i, content_chunk in enumerate(content_chunks, 1):
            print(f"Processing section {i}/{len(content_chunks)}...")
            
            boundary_prompt = f"""
তুমি একজন বাংলা গণিত শিক্ষক। এই NCTB Class 9 গণিত বইয়ের অংশটি বিশ্লেষণ করো এবং শিক্ষামূলক chunk-এ ভাগ করো।

প্রতিটি chunk:
1. একটি সম্পূর্ণ ধারণা/উদাহরণ/প্রমাণ/সংজ্ঞা হবে
2. ৩০০-১০০০ শব্দের মধ্যে হবে
3. স্বাধীনভাবে বোধগম্য হবে

Content:
{content_chunk}

প্রতিটি chunk এর মধ্যে ---CHUNK_SEPARATOR--- দিয়ে আলাদা করো। কোনো অতিরিক্ত ব্যাখ্যা দিও না, শুধু chunks ফেরত দাও।
"""

            chunks = self._make_api_call_with_retry(boundary_prompt, max_retries=3)
            if chunks:
                all_detected_chunks.extend(chunks)
            
            # Add delay between requests to avoid rate limiting
            if i < len(content_chunks):
                time.sleep(2)
        
        return all_detected_chunks
    
    def _make_api_call_with_retry(self, prompt: str, max_retries: int = 3) -> List[str]:
        """Make API call with retry logic and simple text parsing"""
        
        for attempt in range(max_retries):
            try:
                print(f"  Attempt {attempt + 1}/{max_retries}...")
                
                # Generate content without request_options
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config
                )
                
                # Get response text
                response_text = response.text.strip()
                
                # Split by separator
                chunks = [chunk.strip() for chunk in response_text.split('---CHUNK_SEPARATOR---')]
                
                # Filter out empty chunks
                chunks = [chunk for chunk in chunks if chunk]
                
                if chunks:
                    print(f"  Successfully parsed {len(chunks)} chunks")
                    return chunks
                else:
                    print(f"  No valid chunks found in response")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"  API error on attempt {attempt + 1}: {error_msg}")
                
                # Handle specific timeout errors
                if "504" in error_msg or "timeout" in error_msg.lower() or "deadline" in error_msg.lower():
                    wait_time = (attempt + 1) * 10  # Exponential backoff
                    print(f"  Timeout error. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                elif "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = (attempt + 1) * 30
                    print(f"  Rate limit error. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"  Unexpected error: {e}")
                    break
        
        print(f"  Failed after {max_retries} attempts")
        return []
    
    def create_chunk_objects(self, raw_chunks: List[str]) -> List[Dict]:
        """Convert raw chunk content to structured chunk objects"""
        structured_chunks = []
        
        for i, chunk_content in enumerate(raw_chunks, 1):
            chunk = {
                "chunk_id": f"chunk_{i:03d}",
                "content": chunk_content.strip(),
                "word_count": len(chunk_content.split()),
                "source_file": os.path.basename(self.file_path)
            }
            structured_chunks.append(chunk)
        
        return structured_chunks
    
    def save_chunks(self, chunks: List[Dict], output_file: str = "gemini_detected_boundaries.json"):
        """Save detected chunks to JSON file"""
        output_path = os.path.join(os.path.dirname(self.file_path), output_file)
        
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(chunks, file, ensure_ascii=False, indent=2)
        print(f"Boundaries saved to: {output_path}")
    
    def print_summary(self, chunks: List[Dict]):
        """Print summary of detected boundaries"""
        print(f"\n=== Gemini Boundary Detection Summary ===")
        print(f"Total chunks detected: {len(chunks)}")
        print(f"File: {self.file_path}")
        
        total_words = sum(chunk['word_count'] for chunk in chunks)
        avg_words = total_words / len(chunks) if chunks else 0
        print(f"Total words: {total_words}")
        print(f"Average words per chunk: {avg_words:.1f}")
        
        for chunk in chunks:
            print(f"\n--- {chunk['chunk_id']} ---")
            print(f"Word count: {chunk['word_count']}")
            print(f"Content preview: {chunk['content'][:100]}...")

def main():
    # Configuration
    chapter_file = "/home/risad/projects/mathpix_test/splitted_book/testv1/chapter_01.md"
    api_key = "AIzaSyCCjKJxOQjweJRirVUcoZqb2t8_qEIWOFQ"  # Replace with your actual API key
    
    # Check if file exists
    if not os.path.exists(chapter_file):
        print(f"Error: File not found: {chapter_file}")
        return
    
    # Check file size
    file_size = os.path.getsize(chapter_file)
    print(f"File size: {file_size / 1024:.1f} KB")
    
    if file_size > 500000:  # 500KB
        print("Warning: Large file detected. Consider splitting it first.")
        user_input = input("Continue? (y/n): ")
        if user_input.lower() != 'y':
            return
    
    # Initialize detector
    detector = GeminiBoundaryDetector(chapter_file, api_key)
    
    # Detect boundaries using Gemini
    print("Starting boundary detection with Gemini...")
    raw_chunks = detector.detect_boundaries_with_llm()
    
    if not raw_chunks:
        print("Failed to detect boundaries. Possible issues:")
        print("1. Check your API key")
        print("2. Content might be too large")
        print("3. Network/API server issues")
        print("4. Rate limiting")
        return
    
    # Create structured chunk objects
    chunks = detector.create_chunk_objects(raw_chunks)
    
    # Print summary
    detector.print_summary(chunks)
    
    # Save results
    detector.save_chunks(chunks)
    
    # Optional: Save individual chunk files
    output_dir = os.path.join(os.path.dirname(chapter_file), "gemini_chunks")
    os.makedirs(output_dir, exist_ok=True)
    
    for chunk in chunks:
        chunk_file = os.path.join(output_dir, f"{chunk['chunk_id']}.md")
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(chunk['content'])
    
    print(f"\nIndividual chunk files saved to: {output_dir}")

if __name__ == "__main__":
    main()