from sentence_transformers import SentenceTransformer, util

# 1. Load a pre-trained model
# 'all-MiniLM-L6-v2' is a great balance of speed and performance
model = SentenceTransformer('all-MiniLM-L6-v2')

# 2. Define your sentences
sentences = [
    "The cat sits outside",
    "A man is playing guitar",
    "The new movie is awesome",
    "The feline is resting outdoors"
]

# 3. Encode the sentences (convert to vectors)
embeddings = model.encode(sentences)

# 4. Output the results
for sentence, embedding in zip(sentences, embeddings):
    print(f"Sentence: {sentence}")
    print(f"Vector Shape: {embedding.shape}")
    # Printing the first 5 values of the vector as an example
    print(f"First 5 vector values: {embedding[:5]}\n")

# --- Bonus: Semantic Similarity ---
# Compare the first sentence (index 0) with the last one (index 3)
cosine_score = util.cos_sim(embeddings[0], embeddings[3])

print(f"Similarity between '{sentences[0]}' and '{sentences[3]}': {cosine_score.item():.4f}")