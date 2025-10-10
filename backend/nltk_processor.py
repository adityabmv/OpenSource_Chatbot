import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

class NLTKProcessor:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
    
    def preprocess_text(self, text):
        """
        Preprocess text using NLTK:
        1. Sentence tokenization
        2. Word tokenization
        3. Remove special characters
        4. Convert to lowercase
        5. Remove stopwords
        6. Lemmatization
        """
        # Clean text
        text = re.sub(r'[^\w\s.]', '', text)
        
        # Tokenize into sentences
        sentences = sent_tokenize(text)
        
        processed_sentences = []
        for sentence in sentences:
            # Tokenize words
            words = word_tokenize(sentence.lower())
            
            # Remove stopwords and lemmatize
            words = [
                self.lemmatizer.lemmatize(word) 
                for word in words 
                if word not in self.stop_words and word.isalnum()
            ]
            
            processed_sentences.append(' '.join(words))
            
        print("Processed sentences:", processed_sentences)
        return ' '.join(processed_sentences)
    
    def extract_key_phrases(self, text, max_phrases=5):
        """
        Extract key phrases from text using NLTK
        """
        words = word_tokenize(text.lower())
        words = [
            word for word in words 
            if word not in self.stop_words and word.isalnum()
        ]
        
        # Count word frequencies
        freq_dist = nltk.FreqDist(words)
        
        # Get most common phrases
        key_phrases = freq_dist.most_common(max_phrases)
        print("Key phrases:", key_phrases)
        return ", ".join([phrase[0] for phrase in key_phrases])
    
    def get_sentence_importance(self, text):
        """
        Score sentences by importance using word frequency
        """
        # Tokenize into sentences
        sentences = sent_tokenize(text)
        
        # Get word frequencies
        words = word_tokenize(text.lower())
        words = [word for word in words if word not in self.stop_words]
        freq_dist = nltk.FreqDist(words)
        
        # Score sentences based on word frequencies
        sentence_scores = []
        for sentence in sentences:
            score = sum(freq_dist[word.lower()] 
                       for word in word_tokenize(sentence)
                       if word.lower() not in self.stop_words)
            sentence_scores.append((sentence, score))
            
        return sentence_scores