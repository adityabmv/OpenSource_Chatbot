from nltk_processor import NLTKProcessor

# Create a simple test
if __name__ == "__main__":
    # Initialize the NLTK processor
    processor = NLTKProcessor()
    
    # Test text
    test_text = "This is a simple test sentence. NLTK helps in processing natural language!"
    
    # Test preprocessing
    print("\nTesting preprocessing:")
    processed = processor.preprocess_text(test_text)
    print(f"Original: {test_text}")
    print(f"Processed: {processed}")
    
    # Test key phrase extraction
    print("\nTesting key phrase extraction:")
    key_phrases = processor.extract_key_phrases(test_text)
    print(f"Key phrases: {key_phrases}")
    
    print("\nAll tests completed successfully!")