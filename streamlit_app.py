import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
import io
import base64
from PIL import Image
from rag_system import RAGSystem

# Charger les variables d'environnement
load_dotenv()

# Configuration de la page
st.set_page_config(
    page_title="ChatGPT Document Q&A",
    page_icon="📄",
    layout="wide"
)

# Initialiser le client OpenAI
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

client = OpenAI(api_key=api_key)

# Fonction pour extraire le texte d'un fichier PDF
def extract_text_from_pdf(file):
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except ImportError:
        st.error("PyPDF2 n'est pas installé. Installez-le avec: pip install PyPDF2")
        return None
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF: {str(e)}")
        return None

# Fonction pour extraire le texte d'un fichier DOCX
def extract_text_from_docx(file):
    try:
        from docx import Document
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except ImportError:
        st.error("python-docx n'est pas installé. Installez-le avec: pip install python-docx")
        return None
    except Exception as e:
        st.error(f"Erreur lors de la lecture du DOCX: {str(e)}")
        return None

# Fonction pour extraire le texte d'un fichier TXT
def extract_text_from_txt(file):
    try:
        # Essayer différentes encodages
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                file.seek(0)  # Réinitialiser la position du fichier
                text = file.read().decode(encoding)
                return text
            except UnicodeDecodeError:
                continue
        return file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier texte: {str(e)}")
        return None

# Fonction pour extraire le texte selon le type de fichier
def extract_text(file, file_type):
    if file_type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file)
    elif file_type == "text/plain":
        return extract_text_from_txt(file)
    else:
        st.error(f"Type de fichier non supporté: {file_type}")
        return None

# Fonction pour convertir une image en base64
def image_to_base64(image_file):
    """Convertit un fichier image en base64"""
    try:
        image_bytes = image_file.read()
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return img_base64
    except Exception as e:
        st.error(f"Erreur lors de la conversion de l'image: {str(e)}")
        return None

# Fonction pour déterminer le type MIME d'une image
def get_image_mime_type(image_file):
    """Détermine le type MIME d'une image à partir de son nom"""
    filename = image_file.name.lower()
    if filename.endswith(('.jpg', '.jpeg')):
        return "image/jpeg"
    elif filename.endswith('.png'):
        return "image/png"
    else:
        return "image/jpeg"  # Par défaut

# Fonction pour poser une question à ChatGPT avec le contexte du document ou de l'image
def ask_question(question, document_text=None, image_base64=None, model="gpt-4o"):
    try:
        messages = [
            {"role": "system", "content": "Tu es un assistant qui répond aux questions en te basant sur le contenu des documents ou images fournis."}
        ]
        
        # Construire le message utilisateur
        user_content = []
        
        # Si on a une image, utiliser l'API Vision
        if image_base64:
            prompt = f"""Question: {question}

Analyse l'image fournie et répond à la question en te basant uniquement sur le contenu visible dans l'image. Si la réponse n'est pas dans l'image, dis le clairement et dis "je ne sais pas". Réponds dans la même langue que la question de l'utilisateur."""
            
            user_content.append({
                "type": "text",
                "text": prompt
            })
            
            # Le type MIME sera passé séparément, utiliser image/jpeg par défaut
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}"
                }
            })
            
            # Utiliser un modèle avec vision
            vision_models = ["gpt-4o", "gpt-4-turbo", "gpt-4-vision-preview"]
            if model not in vision_models:
                model = "gpt-4o"  # Utiliser gpt-4o par défaut pour la vision
        
        # Si on a du texte de document
        elif document_text:
            # Utiliser RAG si disponible, sinon utiliser tout le texte
            if hasattr(st.session_state, 'rag_system') and st.session_state.get('use_rag', True):
                rag_system = st.session_state['rag_system']
                context = rag_system.get_context_for_question(question, top_k=3)
                
                if context:
                    prompt = f"""Voici les extraits pertinents d'un document trouvés par recherche sémantique :

{context}

Question: {question}

Répond à la question en te basant uniquement sur les extraits du document fournis ci-dessus. Si la réponse n'est pas dans ces extraits, dis le clairement et dis "je ne sais pas". Réponds dans la même langue que la question de l'utilisateur."""
                else:
                    # Fallback si RAG ne trouve rien
                    prompt = f"""Voici le contenu d'un document :

{document_text}

Question: {question}

Répond à la question en te basant uniquement sur le contenu du document fournis. Si la réponse n'est pas dans le document, dis le clairement et dis "je ne sais pas". Réponds dans la même langue que la question de l'utilisateur."""
            else:
                # Mode sans RAG : envoyer tout le document
                prompt = f"""Voici le contenu d'un document :

{document_text}

Question: {question}

Répond à la question en te basant uniquement sur le contenu du document fournis. Si la réponse n'est pas dans le document, dis le clairement et dis "je ne sais pas". Réponds dans la même langue que la question de l'utilisateur."""
            
            user_content.append({"type": "text", "text": prompt})
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur lors de la communication avec ChatGPT: {str(e)}"

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
    
    # Option pour activer/désactiver RAG
    if 'use_rag' not in st.session_state:
        st.session_state['use_rag'] = True
    
    use_rag = st.checkbox(
        "🔍 Utiliser RAG (Recherche intelligente)",
        value=st.session_state['use_rag'],
        help="Active la recherche sémantique dans les documents. Seules les parties pertinentes seront envoyées à ChatGPT."
    )
    st.session_state['use_rag'] = use_rag
    
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
                document_text = extract_text(file_io, uploaded_file.type)
                
                if document_text:
                    st.session_state['document_text'] = document_text
                    st.session_state['current_file'] = uploaded_file.name
                    st.session_state['current_image'] = None  # Réinitialiser l'image
                    
                    # Construire l'index RAG si activé
                    if st.session_state.get('use_rag', True):
                        with st.spinner("🔍 Construction de l'index RAG (cela peut prendre quelques secondes)..."):
                            try:
                                rag_system = RAGSystem(api_key)
                                rag_system.build_index(document_text)
                                st.session_state['rag_system'] = rag_system
                                st.success(f"✅ Index RAG créé avec {len(rag_system.chunks)} chunks!")
                            except Exception as e:
                                st.warning(f"⚠️ Erreur lors de la création de l'index RAG: {str(e)}. Le mode sans RAG sera utilisé.")
                                st.session_state['rag_system'] = None
                    else:
                        st.session_state['rag_system'] = None
                    
                    st.success("✅ Contenu extrait avec succès!")
                else:
                    st.error("❌ Impossible d'extraire le contenu du document.")
                    st.stop()
        
        # Afficher un aperçu du document
        with st.expander("📖 Aperçu du document (premiers 500 caractères)"):
            preview_text = st.session_state['document_text'][:500]
            st.text(preview_text)
            if len(st.session_state['document_text']) > 500:
                st.caption(f"... ({len(st.session_state['document_text']) - 500} caractères supplémentaires)")
            
            # Afficher les infos RAG
            if st.session_state.get('use_rag', True) and hasattr(st.session_state, 'rag_system') and st.session_state.get('rag_system'):
                rag_system = st.session_state['rag_system']
                st.info(f"🔍 RAG activé : {len(rag_system.chunks)} chunks créés pour la recherche sémantique")
            elif not st.session_state.get('use_rag', True):
                st.info("ℹ️ RAG désactivé : tout le document sera envoyé à ChatGPT")
    
    # Gérer les images
    if uploaded_image is not None:
        # Convertir l'image en base64
        if 'current_image' not in st.session_state or st.session_state.get('current_image_name') != uploaded_image.name:
            with st.spinner("Traitement de l'image..."):
                uploaded_image.seek(0)  # Réinitialiser la position
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
        
        # Afficher l'image
        st.subheader("🖼️ Image à analyser")
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
                if document_text and st.session_state.get('use_rag', True) and hasattr(st.session_state, 'rag_system') and st.session_state.get('rag_system'):
                    rag_info = " (avec RAG)"
                
                with st.spinner(f"🤔 ChatGPT ({model}) analyse{rag_info}..."):
                    answer = ask_question(
                        question, 
                        document_text=document_text,
                        image_base64=image_base64,
                        model=model
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

