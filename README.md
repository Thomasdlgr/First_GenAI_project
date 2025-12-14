# Projet ChatGPT - Document Q&A

Ce projet contient deux applications :
1. **chatgpt_hello.py** - Script simple pour tester ChatGPT
2. **streamlit_app.py** - Application web pour poser des questions sur des documents

## Configuration Python 3.12

Ce projet utilise Python 3.12. Sur Windows, utilisez la commande `py -3.12` au lieu de `python`.

### Installation des dépendances

```powershell
py -3.12 -m pip install -r requirements.txt
```

### Exécution des applications

**1. Script simple (chatgpt_hello.py) :**
```powershell
python chatgpt_hello.py
```

**2. Application Streamlit (streamlit_app.py) :**
```powershell
streamlit run streamlit_app.py
```

L'application Streamlit s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`

### Configuration de l'alias (optionnel)

Pour utiliser `python` au lieu de `py -3.12`, exécutez dans PowerShell :

```powershell
. .\setup_python.ps1
```

Ensuite vous pourrez utiliser :
```powershell
python --version
python chatgpt_hello.py
```


## Application Streamlit - Document & Image Q&A

L'application Streamlit permet de :
-  Uploader des documents (PDF, DOCX, TXT) **ou des images** (JPG, PNG)
-  Extraire automatiquement le contenu des documents
-  **Système RAG (Retrieval-Augmented Generation)** : recherche sémantique intelligente dans les documents
-  Analyser les images avec ChatGPT Vision
-  Poser des questions sur le document ou l'image
-  Obtenir des réponses de ChatGPT basées sur le contenu
-  Choisir le modèle ChatGPT (gpt-3.5-turbo, gpt-4, gpt-4o, etc.)

### Formats supportés :
**Documents :**
- **PDF** (.pdf)
- **Word** (.docx)
- **Texte** (.txt)

**Images :**
- **JPEG** (.jpg, .jpeg)
- **PNG** (.png)

### Utilisation :
1. Lancez l'application : `python -m streamlit run streamlit_app.py`
2. Dans la barre latérale, choisissez "Document" ou "Image"
3. Uploadez votre fichier
4. **Pour les images** : Le modèle sera automatiquement changé en `gpt-4o` si nécessaire
5. Posez vos questions dans la zone de texte
6. Consultez l'historique de vos questions/réponses

### Système RAG (Retrieval-Augmented Generation)


**Activation/Désactivation :**
- Cochez/décochez "Utiliser RAG" dans la sidebar
- Par défaut, RAG est activé pour les documents

### Analyse d'images

L'application utilise ChatGPT Vision pour analyser les images :
- Les images sont converties en base64 et envoyées à l'API Vision
- Vous pouvez poser des questions sur le contenu visuel (graphiques, diagrammes, tableaux, photos, etc.)
- Le modèle **gpt-4o** est recommandé et sera utilisé automatiquement pour les images
- Les réponses sont basées uniquement sur le contenu visible dans l'image

## Cheminement du projet

### Phase 1 : Envoi complet du document au LLM
**Limite :** Coûts élevés en termes d'appels API (envoi de tout le document à chaque question)

### Phase 2 : Mise en place d'un système RAG
**Limites :**
- Si la réponse se trouve dans deux chunks différents, la recherche vectorielle peut sélectionner des chunks non pertinents. La question se trouve vectoriellement "au milieu" des deux bons chunks, mais peut être plus proche sémantiquement d'un autre chunk qui ne contient pas la réponse.
- Inadapté pour les résumés de documents (nécessite une vue d'ensemble)

### Phase 3 : Implémentation d'une solution naïve pour les limites du RAG
- Si un document est plus long que 80 pages alors on utilise l'algorithme de RAG sinon on charge au LLM l'entièreté du document.

