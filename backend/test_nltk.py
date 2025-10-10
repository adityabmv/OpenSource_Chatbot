import nltk

def download_nltk_data():
    print("Downloading required NLTK data...")
    try:
        # Download required NLTK data
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')
        nltk.download('punkt_tab')
        print("Successfully downloaded NLTK data!")
        return True
    except Exception as e:
        print(f"Error downloading NLTK data: {str(e)}")
        return False

if __name__ == "__main__":
    download_nltk_data()