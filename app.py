import streamlit as st
import requests
import json
from datetime import datetime, timedelta, timezone
from PIL import Image
import io
import base64
import re
import streamlit.components.v1 as components
import hashlib # Gardé pour le hashage de la clé de rendu
import os
from supabase import create_client, Client
import secrets as python_secrets
import uuid
import bcrypt # Nouvelle dépendance de sécurité

# Configuration de la page
st.set_page_config(
    page_title="Frejus AI",
    page_icon="🧠",
    layout="centered"
)

# --- CSS PERSONNALISÉ POUR LE NOUVEAU DESIGN ---
def load_css():
    css = """
    <style>
        /* --- Styles Globaux --- */
        body {
            background-color: #0e1117; /* Fond sombre */
        }
        
        /* Conteneur principal */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* --- Page de Connexion/Inscription --- */
        
        /* Conteneur pour centrer le formulaire */
        .login-container {
            background-color: #1a1c24; /* Fond de la carte */
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            margin-top: 2rem;
        }
        
        /* En-tête du formulaire */
        .login-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 1.5rem;
        }
        
        /* Boutons des onglets (Connexion / Inscription) */
        button[data-baseweb="tab"] {
            background-color: transparent;
            color: #a0a0a5;
            border-radius: 8px;
            font-weight: 500;
        }
        /* Onglet actif */
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: #2c2f3b;
            color: white;
        }
        
        /* Champs de saisie */
        input[type="text"], input[type="password"], input[type="email"] {
            background-color: #2c2f3b; /* Fond du champ */
            color: white;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 10px 12px;
        }
        
        /* Bouton principal */
        .stButton button {
            background-color: #0068c9; /* Bleu principal */
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 0;
            font-weight: 600;
            transition: background-color 0.2s ease;
        }
        .stButton button:hover {
            background-color: #0055a6; /* Bleu plus sombre au survol */
        }
        
        /* Checkbox "Se souvenir de moi" */
        .stCheckbox {
            color: #a0a0a5;
        }

        /* --- Interface de Chat Principale --- */

        /* En-tête du chat */
        .header-container {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid #2c2f3b;
            padding-bottom: 1rem;
        }
        
        /* Sidebar */
        .stSidebar {
            background-color: #1a1c24; /* Fond de la sidebar */
            border-right: 1px solid #2c2f3b;
        }
        .stSidebar [data-testid="stHeader"] {
            color: white;
            font-size: 1.5rem;
        }
        .stSidebar .stSelectbox, .stSidebar .stRadio {
            background-color: #2c2f3b;
            border-radius: 8px;
            padding: 10px;
        }

        /* Messages du Chat */
        [data-testid="stChatMessage"] {
            background-color: #2c2f3b;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.5rem;
        }
        /* Avatar dans le chat */
        [data-testid="stChatMessage"] .stAvatar {
            background-color: #444;
            padding: 5px;
            border-radius: 50%;
        }
        
        /* Message utilisateur */
        [data-testid="stChatMessage"][data-testid="stChatMessage-user"] {
            background-color: #0068c9; /* Fond bleu pour l'utilisateur */
            color: white;
        }

        /* Zone de saisie du chat */
        [data-testid="stChatInput"] {
            background-color: #1a1c24; /* Fond de la barre de saisie */
            border-top: 1px solid #2c2f3b;
        }
        [data-testid="stChatInput"] textarea {
            background-color: #2c2f3b;
            color: white;
            border-radius: 8px;
        }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Appeler la fonction CSS
load_css()

# Configuration Supabase et Groq
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")

# Vérifier la configuration
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Configuration Supabase manquante.")
    st.stop()

if not GROQ_API_KEY:
    st.error("⚠️ Clé API Groq manquante.")
    st.stop()

# Initialiser Supabase
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# Fonctions pour gérer les cookies via localStorage (plus fiable que les cookies)
def set_local_storage(key, value):
    """Sauvegarder dans localStorage"""
    js_code = f"""
    <script>
        localStorage.setItem('{key}', '{value}');
        console.log('Token saved to localStorage: {value}');
    </script>
    """
    components.html(js_code, height=0)

def get_local_storage_value(component_key):
    """
    Récupérer la valeur depuis localStorage via un composant Streamlit.
    Nous utilisons 'component_key' pour cibler ce composant spécifique.
    """
    js_code = f"""
    <script>
        const value = localStorage.getItem('frejus_session');
        const data = {{
            value: value || ''
        }};
        
        // Envoyer via Streamlit en ciblant le 'key' du composant
        window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: JSON.stringify(data),
            key: '{component_key}'
        }}, '*');
    </script>
    """
    
    # --- CORRECTION DE LA TYPERROR ---
    # 1. 'key=component_key' est ajouté pour que postMessage puisse le cibler.
    # 2. 'default="COMPONENT_INIT"' (un string) est ajouté pour correspondre
    #    au type de retour (JSON string) et éviter le TypeError.
    result = components.html(js_code, height=0, key=component_key, default="COMPONENT_INIT")
    
    try:
        # Gérer la valeur d'init
        if result == "COMPONENT_INIT":
            return "COMPONENT_INIT"
            
        if result:
            data = json.loads(result)
            return data.get('value', '')
    except:
        pass
    
    return None

def clear_local_storage(key):
    """Supprimer de localStorage"""
    js_code = f"""
    <script>
        localStorage.removeItem('{key}');
        console.log('Token removed from localStorage');
    </script>
    """
    components.html(js_code, height=0)

# --- Fonctions d'authentification sécurisées (bcrypt restauré) ---

def get_password_hash(password):
    """Génère un hachage sécurisé bcrypt pour un mot de passe"""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def check_password_hash(password, stored_hash):
    """Vérifie un mot de passe par rapport à un hachage bcrypt existant"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception as e:
        # Gère les hachages invalides ou autres erreurs
        return False

def generate_session_token():
    return python_secrets.token_urlsafe(32)

def create_session(user_id, username):
    """Créer une session persistante"""
    try:
        token = generate_session_token()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        # Supprimer les anciennes sessions de cet utilisateur
        supabase.table('sessions').delete().eq('user_id', user_id).execute()
        
        # Créer la nouvelle session
        supabase.table('sessions').insert({
            'user_id': user_id,
            'token': token,
            'expires_at': expires_at
        }).execute()
        
        return token
    except Exception as e:
        st.error(f"Erreur création session: {str(e)}")
        return None

def get_session(token):
    """Vérifier si une session est valide"""
    if not token:
        return None
    
    try:
        result = supabase.table('sessions').select('user_id, expires_at, users(id, username, email)').eq('token', token).execute()
        
        if result.data and len(result.data) > 0:
            session = result.data[0]
            expires_str = session['expires_at']
            
            # Gérer différents formats de date (Supabase utilise 'Z' ou '+00:00')
            if expires_str.endswith('Z'):
                expires_str = expires_str.replace('Z', '+00:00')
            
            # S'assurer que le format est géré
            if '+' not in expires_str.split('T')[1]:
                if '.' in expires_str:
                        expires_at = datetime.strptime(expires_str, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
                else:
                        expires_at = datetime.strptime(expires_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            else:
                    expires_at = datetime.fromisoformat(expires_str)

            # S'assurer que les deux dates sont "aware" (conscientes du fuseau horaire)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
                
            now = datetime.now(timezone.utc)
            
            # Vérifier si la session n'est pas expirée
            if now < expires_at:
                user = session['users']
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email']
                }
        
        return None
    except Exception as e:
        st.error(f"Erreur vérification session: {str(e)}")
        return None

def delete_session(token):
    """Supprimer une session"""
    try:
        supabase.table('sessions').delete().eq('token', token).execute()
        return True
    except Exception as e:
        st.error(f"Erreur suppression session: {str(e)}")
        return False

def register_user(username, password, email):
    """Inscrire un nouvel utilisateur avec hachage bcrypt"""
    try:
        # Vérifier si le nom d'utilisateur existe
        result_user = supabase.table('users').select('id').eq('username', username).execute()
        if result_user.data:
            return False, "Nom d'utilisateur déjà pris"
        
        # Vérifier si l'email existe
        result_email = supabase.table('users').select('id').eq('email', email).execute()
        if result_email.data:
            return False, "Email déjà utilisé"
        
        # Hasher le mot de passe avec bcrypt
        user_data = {
            'username': username,
            'password_hash': get_password_hash(password),
            'email': email
        }
        result = supabase.table('users').insert(user_data).execute()
        
        if result.data:
            user_id = result.data[0]['id']
            # Créer une conversation initiale
            supabase.table('conversations').insert({
                'user_id': user_id,
                'name': 'Conversation 1'
            }).execute()
            return True, "Compte créé avec succès !"
        
        return False, "Erreur lors de la création du compte"
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def login_user(username, password):
    """Connecter un utilisateur avec vérification bcrypt"""
    try:
        result = supabase.table('users').select('*').eq('username', username).execute()
        
        if not result.data:
            return False, "Utilisateur introuvable", None
        
        user = result.data[0]
        
        # Vérifier le mot de passe avec bcrypt
        if not check_password_hash(password, user['password_hash']):
            return False, "Mot de passe incorrect", None
        
        return True, "Connexion réussie !", user['id']
    except Exception as e:
        return False, f"Erreur: {str(e)}", None

# --- Fonctions de gestion des données (Robustesse améliorée) ---

def get_user_conversations(user_id):
    try:
        result = supabase.table('conversations').select('*').eq('user_id', user_id).order('created_at').execute()
        return result.data
    except Exception as e:
        st.error(f"Erreur (get_user_conversations): {str(e)}")
        return []

def get_conversation_messages(conversation_id):
    try:
        result = supabase.table('messages').select('*').eq('conversation_id', conversation_id).order('created_at').execute()
        return result.data
    except Exception as e:
        st.error(f"Erreur (get_conversation_messages): {str(e)}")
        return []

def save_message(conversation_id, role, content):
    try:
        supabase.table('messages').insert({
            'conversation_id': conversation_id,
            'role': role,
            'content': content
        }).execute()
        return True
    except Exception as e:
        st.error(f"Erreur (save_message): {str(e)}")
        return False

def create_conversation(user_id, name):
    try:
        result = supabase.table('conversations').insert({
            'user_id': user_id,
            'name': name
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Erreur (create_conversation): {str(e)}")
        return None

def delete_conversation(conversation_id):
    try:
        # Supprimer d'abord les messages
        supabase.table('messages').delete().eq('conversation_id', conversation_id).execute()
        # Supprimer la conversation
        supabase.table('conversations').delete().eq('id', conversation_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur (delete_conversation): {str(e)}")
        return False

def rename_conversation(conversation_id, new_name):
    try:
        supabase.table('conversations').update({'name': new_name}).eq('id', conversation_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur (rename_conversation): {str(e)}")
        return False

# Initialiser l'état de session
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'session_token' not in st.session_state:
    st.session_state.session_token = None
if 'storage_checked' not in st.session_state:
    st.session_state.storage_checked = False

# Vérifier localStorage au premier chargement uniquement
if not st.session_state.storage_checked and not st.session_state.authenticated:
    
    # Appel de la fonction corrigée
    stored_token = get_local_storage_value(component_key="storage_getter")
    
    # Si ce n'est PAS la valeur d'init (c-à-d que le JS a répondu)
    if stored_token != "COMPONENT_INIT":
        st.session_state.storage_checked = True
        
        if stored_token:
            user = get_session(stored_token)
            if user:
                st.session_state.authenticated = True
                st.session_state.username = user['username']
                st.session_state.user_id = user['id']
                st.session_state.session_token = stored_token
                st.rerun()
    # Si c'est le premier chargement (valeur d'init), ne rien faire
    # 'storage_checked' reste False, on attend le rerun du JS.
    

# Page de connexion/inscription
if not st.session_state.authenticated:
    
    # --- Utilisation du conteneur CSS pour le design ---
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # --- En-tête personnalisé ---
    st.markdown("""
    <div class="login-header">
        <img src="https://api.dicebear.com/7.x/bottts/svg?seed=frejus" width="60">
        <div>
            <h1 style="margin: 0; padding: 0;">🧠 Frejus AI</h1>
            <p style="margin: 0; padding: 0; color: #a0a0a5;">Votre assistant intelligent</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.success("✅ **Connexion persistante** : Restez connecté !")
    
    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Inscription"])
    
    with tab1:
        st.subheader("Connexion")
        login_username = st.text_input("Nom d'utilisateur", key="login_user")
        login_password = st.text_input("Mot de passe", type="password", key="login_pass")
        remember_me = st.checkbox("Se souvenir de moi (30 jours)", value=True)
        
        if st.button("Se connecter", type="primary", use_container_width=True):
            if login_username and login_password:
                success, message, user_id = login_user(login_username, login_password)
                if success:
                    # Créer une session persistante
                    session_token = create_session(user_id, login_username)
                    
                    if session_token:
                        st.session_state.authenticated = True
                        st.session_state.username = login_username
                        st.session_state.user_id = user_id
                        st.session_state.session_token = session_token
                        
                        # Sauvegarder dans localStorage si "Se souvenir de moi" est coché
                        if remember_me:
                            set_local_storage("frejus_session", session_token)
                        
                        st.success(message)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création de la session")
                else:
                    st.error(f"❌ {message}")
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
                elif '@' not in reg_email or '.' not in reg_email:
                    st.error("Email invalide")
                else:
                    success, message = register_user(reg_username, reg_password, reg_email)
                    if success:
                        st.success(message)
                        st.balloons()
                        st.info("✅ Connectez-vous maintenant !")
                    else:
                        st.error(f"❌ {message}")
            else:
                st.warning("Veuillez remplir tous les champs")
    
    st.markdown("</div>", unsafe_allow_html=True) # Ferme login-container
    st.stop()

# --- Interface principale de l'application ---
# Ce code n'est atteint que si st.session_state.authenticated EST True

# Recharger les conversations si nécessaire (ex: après création/suppression)
if 'conversations' not in st.session_state or st.session_state.get('reload_conversations', True):
    conversations_data = get_user_conversations(st.session_state.user_id)
    if conversations_data:
        st.session_state.conversations = {conv['id']: conv['name'] for conv in conversations_data}
        st.session_state.conversations_ids = {conv['name']: conv['id'] for conv in conversations_data}
        
        # S'assurer que current_conversation est valide, sinon réinitialiser
        if st.session_state.get('current_conversation') not in st.session_state.conversations_ids:
            st.session_state.current_conversation = conversations_data[0]['name']
            st.session_state.current_conversation_id = conversations_data[0]['id']
    else:
        # Gérer le cas où toutes les conversations sont supprimées
        # ou un nouvel utilisateur sans conversation (corrigé à l'inscription)
        st.session_state.conversations = {}
        st.session_state.conversations_ids = {}
        
    st.session_state.reload_conversations = False

# Assurer qu'il y a toujours au moins une conversation
if not st.session_state.conversations and st.session_state.user_id:
    # Si l'utilisateur n'a AUCUNE conversation (par ex. ancien utilisateur avant la MAJ)
    default_conv = create_conversation(st.session_state.user_id, "Conversation 1")
    if default_conv:
        st.session_state.reload_conversations = True
        st.rerun()
    else:
        st.error("Erreur critique : impossible de créer une conversation de base.")
        st.stop()

# --- En-tête de l'application (Design amélioré) ---
st.markdown("""
<div class="header-container">
    <img src="https://api.dicebear.com/7.x/bottts/svg?seed=frejus" width="60">
    <div>
        <h1 style="margin: 0; padding: 0;">🧠 Frejus AI</h1>
        <p style="margin: 0; padding: 0; color: #a0a0a5;">Propulsé par Groq</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Colonne pour le bouton de déconnexion (placé à droite)
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown(f"Bienvenue, **{st.session_state.username}** !")
with col2:
    if st.button("🚪 Déconnexion", key="logout", help="Déconnexion", use_container_width=True):
        # Supprimer la session et le localStorage
        if st.session_state.session_token:
            delete_session(st.session_state.session_token)
            clear_local_storage("frejus_session")
        
        # Réinitialiser tous les états de session
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.session_state.authenticated = False
        st.session_state.storage_checked = False
        
        st.success("✅ Déconnexion réussie")
        st.rerun()


# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.markdown("---")
    st.markdown("### 📚 Mode de conversation")
    
    model_category = st.radio(
        "Catégorie",
        ["💬 Conversation générale", "💻 Codage expert", "🎨 Design créatif"],
        label_visibility="collapsed"
    )
    
    if model_category == "💬 Conversation générale":
        model = st.selectbox("Modèle IA", ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"])
        st.session_state.code_mode = False
        st.session_state.design_mode = False
    elif model_category == "💻 Codage expert":
        model = st.selectbox("Modèle IA", ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"])
        st.session_state.code_mode = True
        st.session_state.design_mode = False
        st.info("🔧 Mode codage actif")
    else:
        model = st.selectbox("Modèle IA", ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"])
        st.session_state.design_mode = True
        st.session_state.code_mode = False
        st.success("🎨 Mode design actif")
    
    st.markdown("---")
    st.markdown("### 💬 Mes conversations")
    
    if st.session_state.conversations:
        conversation_names = list(st.session_state.conversations.values())
        
        # Gérer le cas où la conversation actuelle n'existe plus
        current_index = 0
        if 'current_conversation' in st.session_state and st.session_state.current_conversation in conversation_names:
            current_index = conversation_names.index(st.session_state.current_conversation)
        else:
            # Si la conversation n'existe pas, prendre la première
            st.session_state.current_conversation = conversation_names[0]
            st.session_state.current_conversation_id = st.session_state.conversations_ids[conversation_names[0]]

        
        selected_conv = st.selectbox("Conversation active", conversation_names, index=current_index, label_visibility="collapsed")
        
        if selected_conv != st.session_state.current_conversation:
            st.session_state.current_conversation = selected_conv
            st.session_state.current_conversation_id = st.session_state.conversations_ids[selected_conv]
            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Nouvelle", use_container_width=True):
            conv_count = len(st.session_state.conversations) + 1
            new_conv = create_conversation(st.session_state.user_id, f"Conversation {conv_count}")
            if new_conv:
                st.session_state.reload_conversations = True
                st.rerun()
    
    with col2:
        if st.button("🗑️ Supprimer", use_container_width=True):
            if len(st.session_state.conversations) > 1:
                delete_conversation(st.session_state.current_conversation_id)
                st.session_state.reload_conversations = True
                st.rerun()
            else:
                st.error("Gardez au moins 1 conversation")
    
    new_name = st.text_input("Renommer", value=st.session_state.current_conversation, key="rename")
    if new_name != st.session_state.current_conversation and new_name.strip():
        if new_name not in st.session_state.conversations_ids:
            rename_conversation(st.session_state.current_conversation_id, new_name)
            st.session_state.reload_conversations = True
            st.rerun()
        else:
            st.warning("Ce nom existe déjà.")
    
    st.markdown("---")
    msg_count = len(get_conversation_messages(st.session_state.current_conversation_id))
    st.metric("Messages", msg_count)
    st.metric("Conversations", len(st.session_state.conversations))

# Fonctions utilitaires
def render_html_if_present(response_text):
    """Affiche le texte et les aperçus HTML de manière entrelacée"""
    html_pattern = r'```html\n(.*?)\n```'
    parts = re.split(html_pattern, response_text, flags=re.DOTALL)
    
    if len(parts) == 1: # Pas de HTML trouvé
        return False
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # C'est du texte normal
            if part.strip():
                st.markdown(part)
        else:
            # C'est le code HTML
            html_code = part
            # Utiliser un hash du code pour une clé unique
            key_hash = hashlib.md5(html_code.encode()).hexdigest()
            if st.button(f"👁️ Aperçu", key=f"render_{i}_{key_hash}", type="primary"):
                components.html(html_code, height=600, scrolling=True)
            with st.expander(f"📝 Code"):
                st.code(html_code, language='html')
    return True

def call_groq_api(messages, model, code_mode=False, design_mode=False):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    clean_messages = []
    
    if code_mode:
        clean_messages.append({"role": "system", "content": "Tu es un expert en programmation. Tu fournis des réponses claires, du code propre, commenté et complet. Tu es spécialisé dans tous les langages de programmation."})
    elif design_mode:
        clean_messages.append({"role": "system", "content": "Tu es un expert en design UI/UX et en développement frontend. Si on te demande de créer quelque chose, tu réponds *exclusivement* avec du code HTML, CSS et JS dans un bloc ```html. Si on te pose une question, tu réponds normalement en texte."})
    else:
        clean_messages.append({"role": "system", "content": "Tu es un assistant IA polyvalent nommé Frejus AI. Tu es serviable, créatif et honnête."})

    
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
        return result["choices"][0]["message"]["content"] if "choices" in result else "❌ Erreur de réponse de l'API"
    except requests.exceptions.Timeout:
        return "❌ Erreur : Le délai de réponse de l'API (60s) a été dépassé."
    except requests.exceptions.RequestException as e:
        return f"❌ Erreur de connexion à l'API: {str(e)}"
    except Exception as e:
        return f"❌ Erreur inconnue: {str(e)}"

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
if prompt := st.chat_input("💬 Écrivez votre message..."):
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
            
            if st.session_state.get("design_mode"):
                if not render_html_if_present(response):
                    st.markdown(response)
            else:
                st.markdown(response)
    
    save_message(st.session_state.current_conversation_id, "assistant", response)
    st.rerun()

if not messages:
    st.info("""
    ### 👋 Bienvenue dans Frejus AI !
    
    **Suggestions pour commencer :**
    
    💬 **Conversation** : "Explique-moi la physique quantique"
    💻 **Codage** : "Crée une API REST en Python"
    🎨 **Design** : "Design une carte de profil moderne"
    """)
