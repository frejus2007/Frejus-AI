import streamlit as st
import requests
import json
from datetime import datetime
from PIL import Image
import io
import base64
import re
import streamlit.components.v1 as components
import hashlib
import os
from supabase import create_client, Client

# Configuration de la page
st.set_page_config(
    page_title="Frejus AI",
    page_icon="🧠",
    layout="centered"
)

# Configuration Supabase et Groq
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")

# Vérifier la configuration
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Configuration Supabase manquante.")
    st.info("""
    ### Ajoutez dans les secrets Streamlit :
    ```toml
    SUPABASE_URL = "votre_url"
    SUPABASE_KEY = "votre_clé"
    GROQ_API_KEY = "votre_clé_groq"
    ```
    """)
    st.stop()

if not GROQ_API_KEY:
    st.error("⚠️ Clé API Groq manquante dans les secrets Streamlit.")
    st.stop()

# Initialiser Supabase
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# Fonctions d'authentification
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email):
    try:
        result = supabase.table('users').select('*').eq('username', username).execute()
        if result.data:
            return False, "Nom d'utilisateur déjà pris"
        
        user_data = {
            'username': username,
            'password_hash': hash_password(password),
            'email': email
        }
        result = supabase.table('users').insert(user_data).execute()
        
        if result.data:
            user_id = result.data[0]['id']
            supabase.table('conversations').insert({
                'user_id': user_id,
                'name': 'Conversation 1'
            }).execute()
            return True, "Compte créé avec succès !"
        
        return False, "Erreur lors de la création du compte"
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def login_user(username, password):
    try:
        result = supabase.table('users').select('*').eq('username', username).execute()
        
        if not result.data:
            return False, "Utilisateur introuvable", None
        
        user = result.data[0]
        if user['password_hash'] != hash_password(password):
            return False, "Mot de passe incorrect", None
        
        return True, "Connexion réussie !", user['id']
    except Exception as e:
        return False, f"Erreur: {str(e)}", None

def get_user_conversations(user_id):
    try:
        result = supabase.table('conversations').select('*').eq('user_id', user_id).order('created_at').execute()
        return result.data
    except:
        return []

def get_conversation_messages(conversation_id):
    try:
        result = supabase.table('messages').select('*').eq('conversation_id', conversation_id).order('created_at').execute()
        return result.data
    except:
        return []

def save_message(conversation_id, role, content):
    try:
        supabase.table('messages').insert({
            'conversation_id': conversation_id,
            'role': role,
            'content': content
        }).execute()
        return True
    except:
        return False

def create_conversation(user_id, name):
    try:
        result = supabase.table('conversations').insert({
            'user_id': user_id,
            'name': name
        }).execute()
        return result.data[0] if result.data else None
    except:
        return None

def delete_conversation(conversation_id):
    try:
        supabase.table('conversations').delete().eq('id', conversation_id).execute()
        return True
    except:
        return False

def rename_conversation(conversation_id, new_name):
    try:
        supabase.table('conversations').update({'name': new_name}).eq('id', conversation_id).execute()
        return True
    except:
        return False

# Initialiser l'état de session
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Page de connexion/inscription
if not st.session_state.authenticated:
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://api.dicebear.com/7.x/bottts/svg?seed=frejus", width=80)
    with col2:
        st.title("🧠 Frejus AI")
        st.markdown("*Votre assistant intelligent pour résoudre tous vos problèmes*")
    
    st.markdown("---")
    
    st.success("✅ **Gratuit et sans limite** : Aucune clé API requise, utilisez Frejus AI librement !")
    
    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Inscription"])
    
    with tab1:
        st.subheader("Connexion")
        login_username = st.text_input("Nom d'utilisateur", key="login_user")
        login_password = st.text_input("Mot de passe", type="password", key="login_pass")
        
        if st.button("Se connecter", type="primary", use_container_width=True):
            if login_username and login_password:
                success, message, user_id = login_user(login_username, login_password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = login_username
                    st.session_state.user_id = user_id
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Veuillez remplir tous les champs")
    
    with tab2:
        st.subheader("Créer un compte gratuit")
        reg_username = st.text_input("Nom d'utilisateur", key="reg_user", help="Minimum 3 caractères")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Mot de passe", type="password", key="reg_pass", help="Minimum 6 caractères")
        reg_password2 = st.text_input("Confirmer mot de passe", type="password", key="reg_pass2")
        
        if st.button("S'inscrire gratuitement", type="primary", use_container_width=True):
            if reg_username and reg_email and reg_password and reg_password2:
                if len(reg_username) < 3:
                    st.error("Le nom d'utilisateur doit contenir au moins 3 caractères")
                elif reg_password != reg_password2:
                    st.error("Les mots de passe ne correspondent pas")
                elif len(reg_password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères")
                elif '@' not in reg_email:
                    st.error("Email invalide")
                else:
                    success, message = register_user(reg_username, reg_password, reg_email)
                    if success:
                        st.success(message)
                        st.balloons()
                        st.info("✅ Connectez-vous maintenant pour commencer !")
                    else:
                        st.error(message)
            else:
                st.warning("Veuillez remplir tous les champs")
    
    st.markdown("---")
    st.markdown("""
    ### 🎯 Pourquoi choisir Frejus AI ?
    
    - 💬 **Conversations illimitées** : Discutez sans restrictions
    - 💻 **Mode Codage Expert** : Code propre et optimisé
    - 🎨 **Mode Design Créatif** : Interfaces modernes avec animations
    - 📝 **Sauvegarde automatique** : Ne perdez jamais vos conversations
    - 🔐 **100% Sécurisé** : Vos données sont protégées
    - 🆓 **Totalement gratuit** : Pas de carte bancaire requise
    - ☁️ **Accessible partout** : Sur tous vos appareils
    """)
    
    st.stop()

# Interface principale
if 'conversations' not in st.session_state or st.session_state.get('reload_conversations', True):
    conversations_data = get_user_conversations(st.session_state.user_id)
    st.session_state.conversations = {conv['id']: conv['name'] for conv in conversations_data}
    st.session_state.conversations_ids = {conv['name']: conv['id'] for conv in conversations_data}
    if conversations_data:
        st.session_state.current_conversation = conversations_data[0]['name']
        st.session_state.current_conversation_id = conversations_data[0]['id']
    st.session_state.reload_conversations = False

# En-tête
col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    st.image("https://api.dicebear.com/7.x/bottts/svg?seed=frejus", width=80)
with col2:
    st.title("🧠 Frejus AI")
    st.markdown("*Assistant intelligent propulsé par Groq*")
with col3:
    st.markdown(f"👤 **{st.session_state.username}**")
    if st.button("🚪", key="logout", help="Déconnexion"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_id = None
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.success("✅ **API activée** : Prêt à l'emploi !")
    
    st.markdown("---")
    st.markdown("### 📚 Mode de conversation")
    
    model_category = st.radio(
        "Catégorie",
        ["💬 Conversation générale", "💻 Codage expert", "🎨 Design créatif"],
        label_visibility="collapsed"
    )
    
    if model_category == "💬 Conversation générale":
        model = st.selectbox(
            "Modèle IA", 
            ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
            help="Modèles optimisés pour la conversation"
        )
        st.session_state.code_mode = False
        st.session_state.design_mode = False
    elif model_category == "💻 Codage expert":
        model = st.selectbox(
            "Modèle IA", 
            ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
            help="Modèles spécialisés en programmation"
        )
        st.session_state.code_mode = True
        st.session_state.design_mode = False
        st.info("🔧 **Mode actif** : Code propre, commenté et optimisé")
    else:
        model = st.selectbox(
            "Modèle IA", 
            ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
            help="Modèles créatifs pour le design"
        )
        st.session_state.design_mode = True
        st.session_state.code_mode = False
        st.success("🎨 **Mode actif** : Interfaces modernes et animations")
    
    st.markdown("---")
    st.markdown("### 💬 Mes conversations")
    
    if st.session_state.conversations:
        conversation_names = list(st.session_state.conversations.values())
        selected_conv = st.selectbox(
            "Conversation active", 
            conversation_names, 
            index=conversation_names.index(st.session_state.current_conversation),
            label_visibility="collapsed"
        )
        
        if selected_conv != st.session_state.current_conversation:
            st.session_state.current_conversation = selected_conv
            st.session_state.current_conversation_id = st.session_state.conversations_ids[selected_conv]
            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Nouvelle", use_container_width=True, help="Créer une nouvelle conversation"):
            conv_count = len(st.session_state.conversations) + 1
            new_conv = create_conversation(st.session_state.user_id, f"Conversation {conv_count}")
            if new_conv:
                st.session_state.reload_conversations = True
                st.rerun()
    
    with col2:
        if st.button("🗑️ Supprimer", use_container_width=True, help="Supprimer la conversation actuelle"):
            if len(st.session_state.conversations) > 1:
                delete_conversation(st.session_state.current_conversation_id)
                st.session_state.reload_conversations = True
                st.rerun()
            else:
                st.error("Gardez au moins 1 conversation")
    
    new_name = st.text_input(
        "Renommer", 
        value=st.session_state.current_conversation, 
        key="rename",
        help="Cliquez hors du champ pour sauvegarder"
    )
    if new_name != st.session_state.current_conversation and new_name.strip():
        rename_conversation(st.session_state.current_conversation_id, new_name)
        st.session_state.reload_conversations = True
        st.rerun()
    
    st.markdown("---")
    msg_count = len(get_conversation_messages(st.session_state.current_conversation_id))
    st.metric("Messages", msg_count)
    st.metric("Conversations", len(st.session_state.conversations))

# Fonctions utilitaires
def render_html_if_present(response_text):
    html_pattern = r'```html\n(.*?)\n```'
    html_matches = re.findall(html_pattern, response_text, re.DOTALL)
    
    if html_matches:
        for i, html_code in enumerate(html_matches):
            st.markdown(response_text.split('```html')[0])
            if st.button(f"👁️ Aperçu visuel", key=f"render_{i}_{hash(html_code)}", type="primary"):
                components.html(html_code, height=600, scrolling=True)
            with st.expander(f"📝 Voir le code source"):
                st.code(html_code, language='html')
        return True
    return False

def call_groq_api(messages, model, code_mode=False, design_mode=False):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    clean_messages = []
    
    if code_mode:
        clean_messages.append({
            "role": "system", 
            "content": "Tu es un expert en programmation de niveau senior. Fournis du code propre, bien commenté et optimisé selon les meilleures pratiques. Explique tes choix techniques."
        })
    elif design_mode:
        clean_messages.append({
            "role": "system", 
            "content": "Tu es un expert UI/UX et développeur front-end créatif. Pour les QUESTIONS: réponds en texte. Pour CRÉER un design: génère du code HTML/CSS/JS dans des balises ```html avec animations, icônes Font Awesome, et design moderne."
        })
    
    for msg in messages:
        clean_messages.append({"role": msg["role"], "content": msg["content"]})
    
    data = {
        "model": model,
        "messages": clean_messages,
        "temperature": 0.3 if code_mode else (0.8 if design_mode else 0.7),
        "max_tokens": 4096 if (code_mode or design_mode) else 2048
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"] if "choices" in result else "❌ Erreur de réponse"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "❌ Erreur d'authentification API. Contactez l'administrateur."
        elif e.response.status_code == 429:
            return "❌ Limite d'utilisation atteinte. Réessayez dans quelques instants."
        else:
            return f"❌ Erreur serveur: {e.response.status_code}"
    except requests.exceptions.Timeout:
        return "❌ Délai d'attente dépassé. Vérifiez votre connexion internet."
    except Exception as e:
        return f"❌ Erreur inattendue: {str(e)}"

# Afficher les messages
messages = get_conversation_messages(st.session_state.current_conversation_id)

for msg in messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and st.session_state.get("design_mode"):
            if not render_html_if_present(msg["content"]):
                st.markdown(msg["content"])
        else:
            st.markdown(msg["content"])

# Input utilisateur
if prompt := st.chat_input("💬 Écrivez votre message ici..."):
    save_message(st.session_state.current_conversation_id, "user", prompt)
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("🤔 Frejus réfléchit..."):
            messages_for_api = [{"role": m["role"], "content": m["content"]} for m in messages]
            messages_for_api.append({"role": "user", "content": prompt})
            
            response = call_groq_api(
                messages_for_api,
                model,
                st.session_state.get("code_mode", False),
                st.session_state.get("design_mode", False)
            )
            
            if st.session_state.get("design_mode") and not render_html_if_present(response):
                st.markdown(response)
            elif not st.session_state.get("design_mode"):
                st.markdown(response)
    
    save_message(st.session_state.current_conversation_id, "assistant", response)
    st.rerun()

# Message de bienvenue
if not messages:
    st.info("""
    ### 👋 Bienvenue dans Frejus AI !
    
    **Quelques suggestions pour commencer :**
    
    🗣️ **Mode Conversation** :
    - "Explique-moi la physique quantique simplement"
    - "Donne-moi 5 idées de business en 2024"
    - "Comment apprendre Python efficacement ?"
    
    💻 **Mode Codage** :
    - "Crée une API REST en Python avec FastAPI"
    - "Optimise ce code [coller votre code]"
    - "Explique-moi les design patterns"
    
    🎨 **Mode Design** :
    - "Crée une carte de profil utilisateur moderne"
    - "Design un formulaire de contact élégant"
    - "Fais-moi une page de tarification"
    
    ✨ **Astuce** : Soyez précis dans vos demandes pour de meilleurs résultats !
    """)
