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

# Configuration Supabase
# En production, mettez ces valeurs dans Streamlit Secrets
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")

# Vérifier la configuration Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Configuration Supabase manquante. Ajoutez SUPABASE_URL et SUPABASE_KEY dans les secrets Streamlit.")
    st.info("""
    ### Comment configurer les secrets Streamlit :
    
    1. Dans Streamlit Cloud, allez dans les **Settings** de votre app
    2. Section **Secrets**
    3. Ajoutez :
    ```toml
    SUPABASE_URL = "votre_url_supabase"
    SUPABASE_KEY = "votre_clé_anon_publique"
    ```
    """)
    st.stop()

# Initialiser le client Supabase
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# Fonctions d'authentification avec Supabase
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email):
    try:
        # Vérifier si l'utilisateur existe
        result = supabase.table('users').select('*').eq('username', username).execute()
        if result.data:
            return False, "Nom d'utilisateur déjà pris"
        
        # Créer l'utilisateur
        user_data = {
            'username': username,
            'password_hash': hash_password(password),
            'email': email
        }
        result = supabase.table('users').insert(user_data).execute()
        
        if result.data:
            # Créer une première conversation
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

def update_user_api_key(user_id, api_key):
    try:
        supabase.table('users').update({'api_key': api_key}).eq('id', user_id).execute()
        return True
    except:
        return False

def get_user_api_key(user_id):
    try:
        result = supabase.table('users').select('api_key').eq('id', user_id).execute()
        return result.data[0]['api_key'] if result.data else None
    except:
        return None

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
    
    st.success("✅ **Version Production** : Base de données Supabase - Vos données sont sauvegardées de façon permanente !")
    
    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Inscription"])
    
    with tab1:
        st.subheader("Connexion")
        login_username = st.text_input("Nom d'utilisateur", key="login_user")
        login_password = st.text_input("Mot de passe", type="password", key="login_pass")
        
        if st.button("Se connecter", type="primary"):
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
        st.subheader("Créer un compte")
        reg_username = st.text_input("Nom d'utilisateur", key="reg_user", help="Minimum 3 caractères")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Mot de passe", type="password", key="reg_pass", help="Minimum 6 caractères")
        reg_password2 = st.text_input("Confirmer mot de passe", type="password", key="reg_pass2")
        
        if st.button("S'inscrire", type="primary"):
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
                        st.info("✅ Vous pouvez maintenant vous connecter !")
                    else:
                        st.error(message)
            else:
                st.warning("Veuillez remplir tous les champs")
    
    st.markdown("---")
    st.markdown("""
    ### 🎯 Fonctionnalités de Frejus AI
    
    - 💬 **Conversations intelligentes** : Posez n'importe quelle question
    - 💻 **Mode Codage** : Code propre et optimisé
    - 🎨 **Mode Design** : Interfaces modernes avec animations
    - 📝 **Multi-conversations** : Organisez vos discussions
    - 💾 **Sauvegarde permanente** : Données stockées dans Supabase
    - 🔐 **Sécurisé** : Vos données sont protégées
    - ☁️ **Accessible partout** : Connectez-vous de n'importe où
    """)
    
    st.stop()

# Interface principale (après authentification)

# Charger les conversations de l'utilisateur
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
    st.markdown("*Votre assistant intelligent - Version Production*")
with col3:
    st.markdown(f"👤 **{st.session_state.username}**")
    if st.button("🚪 Déconnexion", key="logout"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_id = None
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Clé API
    saved_api_key = get_user_api_key(st.session_state.user_id)
    api_key = st.text_input("Clé API Groq", value=saved_api_key or '', type="password", help="Gratuit sur https://console.groq.com")
    
    if api_key and api_key != saved_api_key:
        update_user_api_key(st.session_state.user_id, api_key)
    
    st.markdown("---")
    st.markdown("### 📚 Modèles")
    
    model_category = st.radio(
        "Catégorie",
        ["💬 Conversation", "💻 Codage", "🎨 Design"],
        label_visibility="collapsed"
    )
    
    if model_category == "💬 Conversation":
        model = st.selectbox("Modèle", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"])
        st.session_state.code_mode = False
        st.session_state.design_mode = False
    elif model_category == "💻 Codage":
        model = st.selectbox("Modèle", ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"])
        st.session_state.code_mode = True
        st.session_state.design_mode = False
        st.info("🔧 Mode codage")
    else:
        model = st.selectbox("Modèle", ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"])
        st.session_state.design_mode = True
        st.session_state.code_mode = False
        st.success("🎨 Mode Design")
    
    st.markdown("---")
    st.markdown("### 💬 Conversations")
    
    if st.session_state.conversations:
        conversation_names = list(st.session_state.conversations.values())
        selected_conv = st.selectbox("Active", conversation_names, index=conversation_names.index(st.session_state.current_conversation))
        
        if selected_conv != st.session_state.current_conversation:
            st.session_state.current_conversation = selected_conv
            st.session_state.current_conversation_id = st.session_state.conversations_ids[selected_conv]
            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Nouvelle"):
            conv_count = len(st.session_state.conversations) + 1
            new_conv = create_conversation(st.session_state.user_id, f"Conversation {conv_count}")
            if new_conv:
                st.session_state.reload_conversations = True
                st.rerun()
    
    with col2:
        if st.button("🗑️ Supprimer"):
            if len(st.session_state.conversations) > 1:
                delete_conversation(st.session_state.current_conversation_id)
                st.session_state.reload_conversations = True
                st.rerun()
            else:
                st.error("Gardez au moins 1 conversation")
    
    new_name = st.text_input("Renommer", value=st.session_state.current_conversation, key="rename")
    if new_name != st.session_state.current_conversation and new_name.strip():
        rename_conversation(st.session_state.current_conversation_id, new_name)
        st.session_state.reload_conversations = True
        st.rerun()
    
    st.markdown("---")
    msg_count = len(get_conversation_messages(st.session_state.current_conversation_id))
    st.markdown(f"💬 **Messages:** {msg_count}")
    st.markdown(f"🗂️ **Conversations:** {len(st.session_state.conversations)}")

# Fonctions utilitaires
def render_html_if_present(response_text):
    html_pattern = r'```html\n(.*?)\n```'
    html_matches = re.findall(html_pattern, response_text, re.DOTALL)
    
    if html_matches:
        for i, html_code in enumerate(html_matches):
            st.markdown(response_text.split('```html')[0])
            if st.button(f"👁️ Voir", key=f"render_{i}_{hash(html_code)}", type="primary"):
                components.html(html_code, height=600, scrolling=True)
            with st.expander(f"📝 Code"):
                st.code(html_code, language='html')
        return True
    return False

def call_groq_api(messages, api_key, model, code_mode=False, design_mode=False):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    clean_messages = []
    
    if code_mode:
        clean_messages.append({"role": "system", "content": "Expert en programmation. Code propre et commenté."})
    elif design_mode:
        clean_messages.append({"role": "system", "content": "Expert UI/UX. Questions=texte. Créations=code HTML dans ```html"})
    
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
        return result["choices"][0]["message"]["content"] if "choices" in result else "❌ Erreur"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

# Afficher les messages
messages = get_conversation_messages(st.session_state.current_conversation_id)

for msg in messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and st.session_state.get("design_mode"):
            if not render_html_if_present(msg["content"]):
                st.markdown(msg["content"])
        else:
            st.markdown(msg["content"])

# Input
if prompt := st.chat_input("Posez votre question..."):
    if not api_key:
        st.error("⚠️ Ajoutez votre clé API Groq")
        st.info("👉 Gratuit sur https://console.groq.com")
    else:
        save_message(st.session_state.current_conversation_id, "user", prompt)
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("🤔 Réflexion..."):
                messages_for_api = [{"role": m["role"], "content": m["content"]} for m in messages]
                messages_for_api.append({"role": "user", "content": prompt})
                
                response = call_groq_api(
                    messages_for_api,
                    api_key,
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

if not api_key and not messages:
    st.info("""
    ### 🚀 Premiers pas
    
    1. Obtenez votre clé API Groq gratuite sur https://console.groq.com
    2. Entrez-la dans la barre latérale ⬅️
    3. Choisissez votre mode (Conversation, Codage, Design)
    4. Commencez à discuter ! 💬
    
    ✨ Toutes vos conversations sont sauvegardées de façon permanente dans Supabase !
    """)
