```yaml
tags:
  - Natural Language Processing
  - Urdu Language
  - Spell Checking
  - Real-Word Errors
  - Machine Learning
date: 2023-09-07
```

This paper introduces a novel [[contextual spell checker]] for detecting and correcting [[real-word errors]] in the [[Urdu language]], a [[low-resourced language]]. It details the development of a comprehensive lexicon and dataset, alongside a hybrid approach combining [[machine learning classifiers]] for error detection and [[n-gram language models]] with [[Damerau-Levenshtein distance]] for error correction and candidate ranking.

*   **Problem Addressed**: The detection and correction of [[real-word errors]] in [[Urdu]], which are words that exist in the lexicon but are used incorrectly in context. Existing [[lexicon-based lookup approaches]] are insufficient for these errors as they lack [[contextual information]].
*   **Language Specificity**: [[Urdu]] is a linguistically complex language with 11 vowels, 41 consonants, phonetically similar pairs, and over 40 forms for nouns and verbs, making it challenging for [[Natural Language Processing]] tasks. This study is the first dedicated effort for real-word error detection and correction in [[Urdu]].
*   **Dataset and Lexicon Development**:
    *   An extensive lexicon of 593,738 words was built by combining various [[Urdu]] corpora.
    *   A dataset for [[real-word errors]] was generated, comprising 125,562 sentences and 2,552,735 words, with errors induced using [[Damerau-Levenshtein distance]] to create [[confusion sets]].
    *   [[Preprocessing]] involved removing unwanted characters, special characters, hyperlinks, extra spaces, numbers, and English words, and converting misspelled [[Urdu]] letters to a canonical form.
*   **Error Detection Methodology**:
    *   [[Word-gram features]] (unigram, bigram, trigram, and combined) were extracted using [[TF-IDF]].
    *   Five [[machine learning classifiers]] were employed: [[Support Vector Machine]] (SVM), [[Naïve Bayes]] (NB), [[Random Forest]] (RF), [[Logistic Regression]] (LR), and [[K-Nearest Neighbor]] (KNN).
    *   Experiments were conducted with error densities of 30% and 40%.
    *   **Results**: [[Logistic Regression]] (LR) with combined features achieved the best performance for detection, with a precision of 0.84, recall of 0.79, and F1-score of 0.81, demonstrating stable performance across different error densities.
*   **Error Correction Methodology**:
    *   Candidate correction words were generated using [[Damerau-Levenshtein distance]].
    *   A [[n-gram language model]] (unigram, bigram, trigram) was used for ranking candidate words based on their contextual relevance.
    *   A novel "proposed approach" was introduced for further ranking when multiple candidate words had the same n-gram frequencies, utilizing a three-trigram or two-bigram back-off mechanism.
    *   **Results**: The combination of [[Damerau-Levenshtein distance]], trigram ranking, and the proposed ranking approach yielded the highest correction accuracy of 83.67%.
*   **Future Work**: Plans include detecting and correcting multiple contextual errors within a single sentence and exploring state-of-the-art [[deep learning models]] for [[Urdu]] real-word error detection and correction.