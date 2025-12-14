"""
Système RAG (Retrieval-Augmented Generation) pour la recherche dans les documents
"""
import os
from openai import OpenAI
from typing import List, Tuple
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

class RAGSystem:
    def __init__(self, api_key: str):
        
        self.client = OpenAI(api_key=api_key)
        self.embedding_model = "text-embedding-3-small"  # Modèle d'embedding OpenAI
        self.chunk_size = 1000  # Taille des chunks en caractères
        self.chunk_overlap = 200  # Chevauchement entre chunks
        self.index = None
        self.chunks = []
        self.embeddings = None
        
    def split_text_into_chunks(self, text: str) -> List[str]:
        """
        Divise le texte en chunks pour le traitement
        
        Args:
            text: Texte à diviser
            
        Returns:
            Liste des chunks de texte
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # Définir la fin du chunk
            end = start + self.chunk_size
            
            # Si on n'est pas à la fin, essayer de couper à un espace ou ponctuation
            if end < text_length:
                # Chercher le dernier espace, point, ou saut de ligne dans les 100 derniers caractères
                for i in range(end, max(start + self.chunk_size - 100, start), -1):
                    if text[i] in ['\n', '.', '!', '?', ' ']:
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Déplacer le début avec overlap
            start = end - self.chunk_overlap
            if start >= text_length:
                break
        
        return chunks
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Crée des embeddings pour une liste de textes
        
        Args:
            texts: Liste de textes à convertir en embeddings
            
        Returns:
            Array numpy des embeddings
        """
        embeddings = []
        
        for text in texts:
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                embedding = response.data[0].embedding
                embeddings.append(embedding)
            except Exception as e:
                print(f"Erreur lors de la création de l'embedding: {str(e)}")
                # Si c'est la première itération et qu'on a une erreur, on ne peut pas déterminer la dimension
                if embeddings:
                    # Utiliser la dimension du premier embedding réussi
                    dim = len(embeddings[0])
                    embeddings.append([0.0] * dim)
                else:
                    # Fallback: text-embedding-3-small a 1536 dimensions
                    embeddings.append([0.0] * 1536)
        
        return np.array(embeddings, dtype='float32')
    
    def build_index(self, document_text: str):
        """
        Construit l'index vectoriel à partir du texte du document
        
        Args:
            document_text: Texte complet du document
        """
        # Diviser le texte en chunks
        self.chunks = self.split_text_into_chunks(document_text)
        
        if not self.chunks:
            raise ValueError("Aucun chunk n'a pu être créé à partir du document")
        
        # Créer les embeddings
        self.embeddings = self.create_embeddings(self.chunks)
        
        # Créer l'index FAISS
        if FAISS_AVAILABLE:
            dimension = self.embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)  # Index L2 (distance euclidienne)
            self.index.add(self.embeddings)
        else:
            # Fallback: stocker les embeddings sans FAISS
            self.index = None
    
    def search_relevant_chunks(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Recherche les chunks les plus pertinents pour une question
        
        Args:
            query: Question de l'utilisateur
            top_k: Nombre de chunks à retourner
            
        Returns:
            Liste de tuples (chunk_text, score) triés par pertinence
        """
        if not self.chunks or self.embeddings is None:
            return []
        
        # Créer l'embedding de la question
        query_embedding = self.create_embeddings([query])[0]
        query_embedding = np.array([query_embedding], dtype='float32')
        
        if FAISS_AVAILABLE and self.index is not None:
            # Recherche avec FAISS
            distances, indices = self.index.search(query_embedding, min(top_k, len(self.chunks)))
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.chunks):
                    # Convertir la distance en score de similarité (plus petit = plus similaire)
                    score = 1 / (1 + distances[0][i])  # Score de similarité
                    results.append((self.chunks[idx], float(score)))
        else:
            # Fallback: recherche par similarité cosinus
            query_vec = query_embedding[0]
            scores = []
            
            for i, chunk_embedding in enumerate(self.embeddings):
                # Similarité cosinus
                dot_product = np.dot(query_vec, chunk_embedding)
                norm_query = np.linalg.norm(query_vec)
                norm_chunk = np.linalg.norm(chunk_embedding)
                
                if norm_query > 0 and norm_chunk > 0:
                    similarity = dot_product / (norm_query * norm_chunk)
                    scores.append((i, similarity))
            
            # Trier par similarité décroissante
            scores.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for idx, score in scores[:top_k]:
                results.append((self.chunks[idx], float(score)))
        
        return results
    
    def get_context_for_question(self, question: str, top_k: int = 3) -> str:
        """
        Récupère le contexte pertinent pour une question
        
        Args:
            question: Question de l'utilisateur
            top_k: Nombre de chunks à inclure
            
        Returns:
            Contexte formaté avec les chunks pertinents
        """
        relevant_chunks = self.search_relevant_chunks(question, top_k)
        
        if not relevant_chunks:
            return ""
        
        context_parts = []
        for i, (chunk, score) in enumerate(relevant_chunks, 1):
            context_parts.append(f"[Extrait {i} - Score: {score:.3f}]\n{chunk}\n")
        
        return "\n".join(context_parts)
    
    def reset(self):
        """Réinitialise le système RAG"""
        self.index = None
        self.chunks = []
        self.embeddings = None

