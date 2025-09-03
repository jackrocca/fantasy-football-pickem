"""
Authentication utilities for the Fantasy Football Pick'em League app.
"""
import streamlit as st


def check_login():
    """Check if user is logged in and handle login flow."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.is_admin = False
    
    if not st.session_state.authenticated:
        show_login()
        return False
    return True


def show_login():
    """Display login form and handle authentication."""
    st.title("🏈 Fantasy Football Pick'em League")
    st.subheader("Please log in to continue")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if authenticate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.is_admin = is_admin(username)
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")


def authenticate_user(username, password):
    """Verify user credentials against secrets.toml."""
    try:
        users = st.secrets.get("users", {})
        return username in users and users[username] == password
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False


def is_admin(username):
    """Check if user has admin privileges."""
    try:
        admins = st.secrets.get("admins", {})
        return admins.get(username, False)
    except Exception:
        return False


def logout():
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.is_admin = False
    st.rerun()


def require_admin():
    """Decorator/helper to require admin access."""
    if not st.session_state.get("is_admin", False):
        st.error("Access denied. Admin privileges required.")
        st.stop()
