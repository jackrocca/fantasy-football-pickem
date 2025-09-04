"""
Authentication utilities for the Fantasy Football Pick'em League app.
"""
import streamlit as st


def check_login():
    """Check if user is logged in and handle login flow."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
    
    if not st.session_state.authenticated:
        show_login()
        return False
    return True


def show_login():
    """Display login form and handle authentication."""
    st.title("🏈 Fantasy Football Pick'em League")
    st.subheader("Please log in to continue")
    
    with st.form("login_form"):
        username = st.selectbox("Username", options=st.secrets.get("users", {}).keys())
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if authenticate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
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




def logout():
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.rerun()


