import streamlit as st
import os
import io
from PIL import Image
from dotenv import load_dotenv
from rag_system import RAGSystem

# Charger les variables d'environnement
load_dotenv()

# Configuration de la page
st.set_page_config(
    page_title="ChatGPT Document Q&A",
    page_icon="📄",
    layout="wide"
)

# Initialiser la clé API
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("⚠️ ERREUR: La clé API OpenAI n'est pas définie.")
    st.info("""
    Pour définir votre clé API :
    1. Créez un fichier `.env` à la racine du projet avec :
       `OPENAI_API_KEY=votre-clé-api-ici`
    2. Ou définissez une variable d'environnement PowerShell :
       `$env:OPENAI_API_KEY="votre-clé-api-ici"`
       """)
    st.stop()

# Importer les fonctions depuis main.py
from main import (
    extract_text,
    count_pages,
    estimate_tokens,
    image_to_base64,
    get_image_mime_type,
    ask_question
)

# Interface Streamlit
st.title("📄 ChatGPT Document & Image Q&A")
st.markdown("---")
st.markdown("""
### Comment utiliser cette application :
1. **Uploadez un document** (PDF, DOCX, TXT) **ou une image** (JPG, PNG)
2. Le contenu sera extrait automatiquement
3. **Posez vos questions** sur le document ou l'image
4. ChatGPT répondra en se basant sur le contenu fourni
""")

# Sidebar pour l'upload de fichier et sélection du modèle
with st.sidebar:
    # Sélecteur de modèle en haut
    st.header("⚙️ Configuration")
    
    # Initialiser le modèle par défaut dans session_state
    if 'selected_model' not in st.session_state:
        st.session_state['selected_model'] = "gpt-3.5-turbo"
    
    # Liste des modèles OpenAI disponibles
    available_models = [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4o",
        "gpt-4o-mini"
    ]
    
    # Sélecteur de modèle
    selected_model = st.selectbox(
        "Modèle ChatGPT",
        options=available_models,
        index=available_models.index(st.session_state['selected_model']) if st.session_state['selected_model'] in available_models else 0,
        help="Sélectionnez le modèle OpenAI à utiliser pour les réponses"
    )
    
    # Mettre à jour le modèle dans session_state
    st.session_state['selected_model'] = selected_model
    
    st.markdown("---")
    
    st.header("📤 Upload Fichier")
    
    # Sélecteur de type de fichier
    file_type_choice = st.radio(
        "Type de fichier",
        options=["Document", "Image"],
        help="Choisissez si vous voulez uploader un document ou une image"
    )
    
    if file_type_choice == "Document":
        uploaded_file = st.file_uploader(
            "Choisissez un document",
            type=['pdf', 'docx', 'txt'],
            help="Formats supportés: PDF, DOCX, TXT",
            key="document_uploader"
        )
        uploaded_image = None
    else:
        uploaded_image = st.file_uploader(
            "Choisissez une image",
            type=['jpg', 'jpeg', 'png'],
            help="Formats supportés: JPG, JPEG, PNG",
            key="image_uploader"
        )
        uploaded_file = None
    
    if uploaded_file is not None:
        st.success(f"✅ Document uploadé: {uploaded_file.name}")
        st.info(f"Taille: {uploaded_file.size} bytes")
        st.info(f"Type: {uploaded_file.type}")
    
    if uploaded_image is not None:
        st.success(f"✅ Image uploadée: {uploaded_image.name}")
        st.info(f"Taille: {uploaded_image.size} bytes")
        # Afficher un aperçu de l'image
        image = Image.open(uploaded_image)
        st.image(image, caption=uploaded_image.name, use_container_width=True)

# Zone principale
if uploaded_file is not None or uploaded_image is not None:
    # Gérer les documents
    if uploaded_file is not None:
        # Extraire le texte du document
        if 'document_text' not in st.session_state or st.session_state.get('current_file') != uploaded_file.name:
            with st.spinner("Extraction du contenu du document..."):
                file_bytes = uploaded_file.read()
                file_io = io.BytesIO(file_bytes)
                try:
                    # Compter le nombre de pages
                    file_io.seek(0)
                    num_pages = count_pages(file_io, uploaded_file.type)
                    
                    # Extraire le texte avec callback de progression pour les PDFs
                    file_io.seek(0)
                    
                    # Afficher la progression uniquement pour les PDFs (qui peuvent contenir des images)
                    if uploaded_file.type == "application/pdf":
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def update_progress(page_num, total_pages, message):
                            progress_bar.progress(page_num / total_pages)
                            status_text.text(message)
                        
                        document_text = extract_text(file_io, uploaded_file.type, progress_callback=update_progress)
                        
                        progress_bar.empty()
                        status_text.empty()
                    else:
                        document_text = extract_text(file_io, uploaded_file.type)
                    
                    if document_text:
                        st.session_state['document_text'] = document_text
                        st.session_state['current_file'] = uploaded_file.name
                        st.session_state['current_image'] = None  # Réinitialiser l'image
                        st.session_state['num_pages'] = num_pages
                        
                        # Estimer le nombre de tokens
                        num_tokens = estimate_tokens(document_text)
                        st.session_state['num_tokens'] = num_tokens
                        
                        # Déterminer automatiquement si on utilise RAG (>= 10 000 tokens)
                        use_rag = num_tokens >= 10000
                        st.session_state['use_rag'] = use_rag
                        
                        if use_rag:
                            with st.spinner("🔍 Construction de l'index RAG (cela peut prendre quelques secondes)..."):
                                try:
                                    rag_system = RAGSystem(api_key)
                                    rag_system.build_index(document_text)
                                    st.session_state['rag_system'] = rag_system
                                    st.success(f"✅ Index RAG créé avec {len(rag_system.chunks)} chunks! (Document: ~{num_tokens:,} tokens)")
                                except Exception as e:
                                    st.warning(f"⚠️ Erreur lors de la création de l'index RAG: {str(e)}. Le mode sans RAG sera utilisé.")
                                    st.session_state['rag_system'] = None
                                    st.session_state['use_rag'] = False
                        else:
                            st.session_state['rag_system'] = None
                            st.info(f"ℹ️ Document de ~{num_tokens:,} tokens : RAG désactivé (seuil: 10 000 tokens)")
                        
                        st.success("✅ Contenu extrait avec succès!")
                    else:
                        st.error("❌ Impossible d'extraire le contenu du document.")
                        st.stop()
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'extraction: {str(e)}")
                    st.stop()
        
        # Afficher un aperçu du document
        with st.expander("📖 Aperçu du document (premiers 500 caractères)"):
            preview_text = st.session_state['document_text'][:500]
            st.text(preview_text)
            if len(st.session_state['document_text']) > 500:
                st.caption(f"... ({len(st.session_state['document_text']) - 500} caractères supplémentaires)")
            
            # Afficher les infos RAG
            num_tokens = st.session_state.get('num_tokens', 0)
            if st.session_state.get('use_rag', False) and hasattr(st.session_state, 'rag_system') and st.session_state.get('rag_system'):
                rag_system = st.session_state['rag_system']
                st.info(f"🔍 RAG activé automatiquement (~{num_tokens:,} tokens ≥ 10 000) : {len(rag_system.chunks)} chunks créés pour la recherche sémantique")
            else:
                st.info(f"ℹ️ RAG désactivé (~{num_tokens:,} tokens < 10 000) : tout le document sera envoyé à ChatGPT")
    
    # Gérer les images
    if uploaded_image is not None:
        # Convertir l'image en base64
        if 'current_image' not in st.session_state or st.session_state.get('current_image_name') != uploaded_image.name:
            with st.spinner("Traitement de l'image..."):
                uploaded_image.seek(0)  # Réinitialiser la position
                try:
                    image_base64 = image_to_base64(uploaded_image)
                    image_mime_type = get_image_mime_type(uploaded_image)
                    
                    if image_base64:
                        st.session_state['current_image'] = image_base64
                        st.session_state['current_image_mime'] = image_mime_type
                        st.session_state['current_image_name'] = uploaded_image.name
                        st.session_state['document_text'] = None  # Réinitialiser le texte
                        st.session_state['current_file'] = None  # Réinitialiser le fichier
                        st.success("✅ Image prête pour l'analyse!")
                    else:
                        st.error("❌ Impossible de traiter l'image.")
                        st.stop()
                except Exception as e:
                    st.error(f"❌ Erreur lors du traitement de l'image: {str(e)}")
                    st.stop()
        
        # Afficher l'image
        st.subheader(" Image à analyser")
        uploaded_image.seek(0)
        image = Image.open(uploaded_image)
        st.image(image, caption=uploaded_image.name, use_container_width=True)
    
    st.markdown("---")
    
    # Zone de questions
    st.header("💬 Posez vos questions")
    
    # Historique des questions/réponses
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    
    # Afficher l'historique
    if st.session_state['chat_history']:
        st.subheader("Historique des questions")
        for i, item in enumerate(st.session_state['chat_history']):
            with st.container():
                # Gérer l'ancien format (sans modèle) et le nouveau format (avec modèle)
                if len(item) == 3:
                    q, a, model = item
                    st.markdown(f"**Question {i+1}:** {q}")
                    st.caption(f"Modèle utilisé: {model}")
                    st.markdown(f"**Réponse:** {a}")
                else:
                    q, a = item
                    st.markdown(f"**Question {i+1}:** {q}")
                    st.markdown(f"**Réponse:** {a}")
                st.markdown("---")
    
    # Formulaire pour poser une question
    with st.form("question_form", clear_on_submit=True):
        question = st.text_area(
            "Votre question:",
            placeholder="Ex: Quel est le sujet principal de ce document?",
            height=100
        )
        submit_button = st.form_submit_button("🔍 Poser la question", use_container_width=True)
        
        if submit_button and question:
            # Déterminer si on analyse un document ou une image
            document_text = st.session_state.get('document_text')
            image_base64 = st.session_state.get('current_image')
            
            if not document_text and not image_base64:
                st.error("❌ Aucun contenu disponible. Veuillez uploader un document ou une image.")
            else:
                # Utiliser gpt-4o par défaut si une image est présente
                model = st.session_state['selected_model']
                if image_base64 and model not in ["gpt-4o", "gpt-4-turbo", "gpt-4-vision-preview"]:
                    model = "gpt-4o"
                    st.info("ℹ️ Le modèle a été automatiquement changé en gpt-4o pour l'analyse d'images.")
                
                # Afficher l'info RAG si activé
                rag_info = ""
                use_rag_flag = st.session_state.get('use_rag', False)
                rag_system = None
                
                if document_text and use_rag_flag and hasattr(st.session_state, 'rag_system') and st.session_state.get('rag_system'):
                    rag_info = " (avec RAG)"
                    rag_system = st.session_state['rag_system']
                
                with st.spinner(f"🤔 ChatGPT ({model}) analyse{rag_info}..."):
                    answer = ask_question(
                        question, 
                        document_text=document_text,
                        image_base64=image_base64,
                        model=model,
                        rag_system=rag_system,
                        use_rag=use_rag_flag
                    )
                    
                    # Ajouter à l'historique avec le modèle utilisé
                    st.session_state['chat_history'].append((question, answer, st.session_state['selected_model']))
                    
                    # Afficher la réponse
                    st.success("✅ Réponse reçue!")
                    st.markdown("### Réponse:")
                    st.markdown(answer)
                    
                    # Rafraîchir pour afficher dans l'historique
                    st.rerun()
    
    # Bouton pour effacer l'historique
    if st.session_state['chat_history']:
        if st.button("🗑️ Effacer l'historique"):
            st.session_state['chat_history'] = []
            st.rerun()

else:
    st.info("👈 Veuillez uploader un document ou une image dans la barre latérale pour commencer.")

