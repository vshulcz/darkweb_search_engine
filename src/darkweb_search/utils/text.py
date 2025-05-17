import string

import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords


nltk.download("punkt", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("stopwords", quiet=True)

_LEMMATIZER = WordNetLemmatizer()
_STOPWORDS = set(stopwords.words("english"))


def preprocess_text(
    text: str,
    lowercase: bool = True,
    remove_punct: bool = True,
    remove_stopwords: bool = True,
    lemmatize: bool = True,
) -> list[str]:
    if not text:
        return []

    if lowercase:
        text = text.lower()
    if remove_punct:
        text = text.translate(str.maketrans("", "", string.punctuation))

    tokens = word_tokenize(text)
    tokens = [tok for tok in tokens if tok.isalpha()]

    if remove_stopwords:
        tokens = [tok for tok in tokens if tok not in _STOPWORDS]

    if lemmatize:
        tokens = [_LEMMATIZER.lemmatize(tok) for tok in tokens]

    return tokens
