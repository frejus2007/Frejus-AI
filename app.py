import streamlit as st
import requests
import json
from datetime import datetime
from PIL import Image
import io
import base64
import re
import streamlit.components.v1 as components

# Configuration de la page
st.set_page_config(
    page_title="Frejus AI",
    page_icon="🧠",
    layout="centered"
)

# Initialiser les sessions dans le state
if "conversations" not in st.session_state:
    st.session_state.conversations = {
        "Conversation 1": []
    }
if "current_conversation" not in st.session_state:
    st.session_state.current_conversation = "Conversation 1"
if "conversation_counter" not in st.session_state:
    st.session_state.conversation_counter = 1

# Titre et description
col1, col2 = st.columns([1, 5])
with col1:
    # Vous pouvez remplacer ce lien par votre propre logo
    st.image("https://api.dicebear.com/7.x/bottts/svg?seed=frejus", width=80)
with col2:
    st.title("🧠 Frejus AI")
    st.markdown("*Votre assistant intelligent pour résoudre tous vos problèmes*")

# Sidebar pour la configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Clé API Groq", type="password", help="Obtenez votre clé gratuite sur https://console.groq.com")
    
    st.markdown("---")
    st.markdown("### 📚 Modèles disponibles")
    
    model_category = st.radio(
        "Catégorie",
        ["💬 Conversation générale", "💻 Codage spécialisé", "🎨 Design & UI/UX"],
        label_visibility="collapsed"
    )
    
    if model_category == "💬 Conversation générale":
        model = st.selectbox(
            "Modèle",
            [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it"
            ],
            help="llama-3.3-70b-versatile est le plus performant"
        )
    elif model_category == "💻 Codage spécialisé":
        model = st.selectbox(
            "Modèle de code",
            [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile", 
                "mixtral-8x7b-32768"
            ],
            help="Modèles optimisés pour le code"
        )
        
        if "code_mode" not in st.session_state:
            st.session_state.code_mode = False
        
        st.session_state.code_mode = True
        st.session_state.design_mode = False
        
        st.info("🔧 Mode codage activé :\n- Code propre et commenté\n- Explications détaillées\n- Bonnes pratiques\n- Debugging expert")
    else:  # Design & UI/UX
        model = st.selectbox(
            "Modèle créatif",
            [
                "llama-3.3-70b-versatile",
                "mixtral-8x7b-32768"
            ],
            help="Modèles optimisés pour le design"
        )
        
        if "design_mode" not in st.session_state:
            st.session_state.design_mode = False
        
        st.session_state.design_mode = True
        st.session_state.code_mode = False
        
        st.success("🎨 Mode Design activé :\n\n✅ Répond normalement aux questions\n✅ Génère du code seulement si demandé\n✅ Interfaces modernes avec icônes\n✅ Animations et designs responsifs")
    
    st.markdown("---")
    st.markdown("### 💬 Gestion des conversations")
    
    # Sélectionner une conversation
    conversation_names = list(st.session_state.conversations.keys())
    selected_conv = st.selectbox(
        "Conversation active",
        conversation_names,
        index=conversation_names.index(st.session_state.current_conversation)
    )
    
    if selected_conv != st.session_state.current_conversation:
        st.session_state.current_conversation = selected_conv
        st.rerun()
    
    # Boutons de gestion
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Nouvelle"):
            st.session_state.conversation_counter += 1
            new_name = f"Conversation {st.session_state.conversation_counter}"
            st.session_state.conversations[new_name] = []
            st.session_state.current_conversation = new_name
            st.rerun()
    
    with col2:
        if st.button("🗑️ Supprimer"):
            if len(st.session_state.conversations) > 1:
                del st.session_state.conversations[st.session_state.current_conversation]
                st.session_state.current_conversation = list(st.session_state.conversations.keys())[0]
                st.rerun()
            else:
                st.error("Impossible de supprimer la dernière conversation")
    
    # Renommer la conversation
    new_name = st.text_input("Renommer la conversation", value=st.session_state.current_conversation)
    if new_name != st.session_state.current_conversation and new_name:
        if new_name not in st.session_state.conversations:
            st.session_state.conversations[new_name] = st.session_state.conversations[st.session_state.current_conversation]
            del st.session_state.conversations[st.session_state.current_conversation]
            st.session_state.current_conversation = new_name
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 🖼️ Ajouter une image")
    uploaded_file = st.file_uploader("Uploader une image", type=['png', 'jpg', 'jpeg'], key="image_upload")
    
    st.markdown("---")
    st.markdown("### ℹ️ Info")
    st.markdown("**Frejus AI** utilise l'API Groq gratuite pour vous offrir des réponses rapides et intelligentes.")
    
    # Statistiques
    current_msgs = st.session_state.conversations[st.session_state.current_conversation]
    st.markdown(f"💬 Messages: {len(current_msgs)}")

# Fonction pour détecter et afficher du HTML
def render_html_if_present(response_text):
    # Chercher des blocs de code HTML
    html_pattern = r'```html\n(.*?)\n```'
    html_matches = re.findall(html_pattern, response_text, re.DOTALL)
    
    if html_matches:
        # Il y a du HTML dans la réponse
        for i, html_code in enumerate(html_matches):
            st.markdown(response_text.split('```html')[0])  # Afficher le texte avant
            
            # Bouton pour afficher/masquer le rendu
            if st.button(f"👁️ Voir le rendu visuel #{i+1}", key=f"render_{i}_{hash(html_code)}"):
                components.html(html_code, height=600, scrolling=True)
            
            # Afficher le code avec option de copie
            with st.expander(f"📝 Voir le code HTML #{i+1}"):
                st.code(html_code, language='html')
        
        return True
    
    # Chercher du HTML sans balises de code
    if '<html' in response_text.lower() or '<!doctype html>' in response_text.lower():
        # Extraire le HTML
        html_start = response_text.lower().find('<!doctype')
        if html_start == -1:
            html_start = response_text.lower().find('<html')
        
        if html_start != -1:
            html_code = response_text[html_start:]
            
            # Afficher le texte avant le HTML
            if html_start > 0:
                st.markdown(response_text[:html_start])
            
            # Bouton pour voir le rendu
            if st.button("👁️ Voir le rendu visuel", key=f"render_raw_{hash(html_code)}"):
                components.html(html_code, height=600, scrolling=True)
            
            with st.expander("📝 Voir le code HTML"):
                st.code(html_code, language='html')
            
            return True
    
    return False
def encode_image(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str, image
    except Exception as e:
        return None, None

# Fonction pour appeler l'API Groq
def call_groq_api(messages, api_key, model, code_mode=False, design_mode=False):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Nettoyer les messages pour l'API (enlever les images car Groq ne supporte pas encore)
    clean_messages = []
    
    # Ajouter un system prompt pour le mode code
    if code_mode:
        clean_messages.append({
            "role": "system",
            "content": """Tu es un expert en programmation de niveau senior. Tes réponses doivent être :
- Code propre, optimisé et suivant les meilleures pratiques
- Bien commenté et facile à comprendre
- Accompagné d'explications claires
- Avec gestion d'erreurs appropriée
- Respectant les conventions du langage utilisé
- Incluant des exemples d'utilisation si pertinent

Pour chaque problème de code :
1. Analyse le problème
2. Propose une solution élégante
3. Explique les choix techniques
4. Suggère des améliorations possibles

Langages d'expertise : Python, JavaScript, Java, C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, TypeScript, SQL, HTML/CSS, et plus."""
        })
    elif design_mode:
        clean_messages.append({
            "role": "system",
            "content": """Tu es un expert en Design UI/UX et développement front-end.

**IMPORTANT : Analyse d'abord la demande de l'utilisateur :**

1. Si l'utilisateur pose une QUESTION ou demande une EXPLICATION (exemples : "comment faire X", "explique-moi Y", "qu'est-ce que Z", "aide-moi à comprendre") :
   → Réponds normalement avec du TEXTE, sans générer de code

2. Si l'utilisateur demande EXPLICITEMENT de CRÉER/DESIGNER quelque chose (exemples : "crée une page", "design un formulaire", "fais-moi un site", "code un bouton") :
   → Alors génère le code HTML/CSS/JS complet

**Quand tu DOIS créer du code HTML :**

TOUJOURS inclure :
1. HTML5 sémantique et structure propre
2. CSS moderne avec :
   - Dégradés et couleurs harmonieuses
   - Animations et transitions fluides
   - Shadows et effets de profondeur
   - Design responsive (mobile-first)
   - Glassmorphism ou design moderne
3. Font Awesome pour les icônes (CDN: https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css)
4. Google Fonts pour typographie élégante
5. JavaScript interactif si nécessaire
6. Palette de couleurs cohérente

**Format de code :**
Mets TOUJOURS le code dans des balises ```html pour qu'il soit bien détecté et rendu visuellement.

**Principes de design :**
- Espacement généreux et breathing room
- Hiérarchie visuelle claire
- Contrastes appropriés
- Micro-interactions engageantes
- Accessibilité (WCAG)
- Performance optimisée

Crée des interfaces qui font dire "WOW !" 🎨✨"""
        })
    
    for msg in messages:
        if "image" not in msg:
            clean_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        else:
            # Pour les messages avec image, on ajoute juste le texte
            clean_messages.append({
                "role": msg["role"],
                "content": msg["content"] + " [Image jointe]"
            })
    
    # Ajuster les paramètres selon le mode
    temperature = 0.3 if code_mode else (0.8 if design_mode else 0.7)
    max_tokens = 4096 if (code_mode or design_mode) else 2048
    
    data = {
        "model": model,
        "messages": clean_messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return "❌ Réponse invalide de l'API. Réessayez."
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "❌ Clé API invalide. Vérifiez votre clé sur https://console.groq.com"
        elif e.response.status_code == 429:
            return "❌ Limite d'utilisation atteinte. Attendez quelques minutes."
        else:
            return f"❌ Erreur HTTP {e.response.status_code}: {e.response.text}"
    except requests.exceptions.Timeout:
        return "❌ Délai d'attente dépassé. Vérifiez votre connexion."
    except Exception as e:
        return f"❌ Erreur inattendue : {str(e)}"

# Récupérer les messages de la conversation actuelle
current_messages = st.session_state.conversations[st.session_state.current_conversation]

# Afficher l'historique des messages
for message in current_messages:
    with st.chat_message(message["role"]):
        if "image" in message:
            st.image(message["image"], width=300)
        
        # Gérer l'affichage du HTML pour les anciens messages
        if message["role"] == "assistant" and st.session_state.get("design_mode", False):
            if not render_html_if_present(message["content"]):
                st.markdown(message["content"])
        else:
            st.markdown(message["content"])

# Input utilisateur
if prompt := st.chat_input("Posez votre question ici..."):
    if not api_key:
        st.error("⚠️ Veuillez entrer votre clé API Groq dans la barre latérale !")
        st.info("👉 Obtenez votre clé gratuite sur https://console.groq.com")
    else:
        # Préparer le message utilisateur
        user_message = {"role": "user", "content": prompt}
        
        # Ajouter l'image si uploadée
        if uploaded_file is not None:
            img_str, img = encode_image(uploaded_file)
            if img:
                user_message["image"] = img
                user_message["content"] = f"{prompt}\n\n[Note: Une image a été jointe. Groq ne supporte pas encore l'analyse d'images, mais je peux répondre à vos questions textuelles.]"
        
        # Ajouter le message utilisateur
        current_messages.append(user_message)
        
        with st.chat_message("user"):
            if "image" in user_message:
                st.image(user_message["image"], width=300)
            st.markdown(prompt)
        
        # Générer et afficher la réponse
        with st.chat_message("assistant"):
            with st.spinner("Réflexion en cours..."):
                # Vérifier les modes activés
                code_mode = st.session_state.get("code_mode", False)
                design_mode = st.session_state.get("design_mode", False)
                response = call_groq_api(
                    current_messages,
                    api_key,
                    model,
                    code_mode,
                    design_mode
                )
                
                # Si c'est du design, essayer de rendre le HTML
                if design_mode and not render_html_if_present(response):
                    st.markdown(response)
                elif not design_mode:
                    st.markdown(response)
        
        # Ajouter la réponse à l'historique
        current_messages.append({"role": "assistant", "content": response})
        
        # Réinitialiser l'upload d'image
        if uploaded_file is not None:
            st.rerun()

# Instructions si aucune clé API
if not api_key and len(current_messages) == 0:
    st.info("""
    ### 🚀 Pour commencer :
    
    1. **Obtenez votre clé API gratuite** :
       - Allez sur https://console.groq.com
       - Créez un compte (gratuit)
       - Générez une clé API
    
    2. **Collez la clé** dans la barre latérale ⬅️
    
    3. **Posez votre première question** ! 💬
    
    4. **Fonctionnalités disponibles** :
       - 💬 Créez plusieurs conversations
       - 🖼️ Uploadez des images
       - 🔄 Changez de modèle
       - ✏️ Renommez vos conversations
    
    **Avantages de Groq :**
    - ✅ Gratuit avec limites généreuses
    - ✅ Ultra-rapide
    - ✅ Modèles puissants (Llama 3.3, Mixtral)
    - ✅ Parfait pour débuter
    """)