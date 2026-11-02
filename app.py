import os
import streamlit as st
from database import (init_db, register_user, authenticate_user, get_topics, create_topic,
                      edit_topic, remove_topic, get_journal, save_journal, remove_journal,
                      dashboard_stats)
from ai_tutor import ask_tutor

st.set_page_config(page_title='AI Python Learning Tracker', page_icon='🐍', layout='wide')
init_db()

DEFAULTS = {'user_id': None, 'username': None, 'account_created': False,
            'topic_form_version': 0, 'journal_form_version': 0,
            'editing_journal_id': None, 'tutor_messages': []}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def show_auth():
    st.title('🐍 AI Python Learning Tracker')
    st.write('Learn Python at your own pace. Your topics, journal, and progress belong to your account.')
    if st.session_state.pop('account_created', False):
        st.success('Account created successfully!')
        st.info('Please log in with your new username and password to continue.')
    login_tab, signup_tab = st.tabs(['Log in', 'Create account'])
    with login_tab:
        with st.form('login_form'):
            username = st.text_input('Username', key='login_username')
            password = st.text_input('Password', type='password', key='login_password')
            submitted = st.form_submit_button('Log in', use_container_width=True)
        if submitted:
            result = authenticate_user(username, password)
            if result:
                st.session_state.user_id, st.session_state.username = result
                st.session_state.tutor_messages = []
                st.rerun()
            st.error('Incorrect username or password.')
    with signup_tab:
        with st.form('signup_form'):
            username = st.text_input('Choose a username', key='signup_username')
            password = st.text_input('Create a password', type='password', key='signup_password')
            confirm = st.text_input('Confirm password', type='password', key='signup_confirm')
            submitted = st.form_submit_button('Create account', use_container_width=True)
        if submitted:
            if not username.strip() or not password:
                st.error('Please enter a username and password.')
            elif len(password) < 8:
                st.error('Password must contain at least 8 characters.')
            elif password != confirm:
                st.error('The passwords do not match.')
            else:
                try:
                    register_user(username, password)
                    st.session_state.account_created = True
                    st.rerun()  # return to login; no automatic sign-in
                except ValueError as error:
                    st.error(str(error))


def sidebar():
    with st.sidebar:
        st.title(f"Hello, {st.session_state.username}")
        page = st.radio('Go to', ['Dashboard', 'My Topics', 'Learning Journal', 'AI Tutor'])
        st.divider()
        if st.button('Log out', use_container_width=True):
            for key in ['user_id', 'username', 'editing_journal_id']:
                st.session_state[key] = None
            st.session_state.tutor_messages = []
            st.rerun()
    return page


def dashboard():
    st.title('Your progress dashboard')
    topics, entries, completed = dashboard_stats(st.session_state.user_id)
    a, b, c = st.columns(3)
    a.metric('Topics', topics)
    b.metric('Journal entries', entries)
    c.metric('Completed topics', completed)
    st.subheader('Your learning topics')
    data = get_topics(st.session_state.user_id)
    if not data:
        st.info('Start by adding your first topic in My Topics.')
    for topic in data:
        with st.container(border=True):
            st.markdown(f"**{topic['title']}** · {topic['status']}")
            if topic['description']:
                st.write(topic['description'])


def topics_page():
    st.title('My Topics')
    st.caption('Add the Python topics you want to learn. There is no fixed syllabus.')
    version = st.session_state.topic_form_version
    with st.form(f'new_topic_form_{version}', clear_on_submit=True):
        title = st.text_input('Topic name', key=f'new_topic_title_{version}', placeholder='e.g. Python functions')
        description = st.text_area('Description or learning goal', key=f'new_topic_description_{version}')
        status = st.selectbox('Status', ['Not started', 'In progress', 'Completed'], key=f'new_topic_status_{version}')
        submitted = st.form_submit_button('Add topic', use_container_width=True)
    if submitted:
        if not title.strip():
            st.error('Please enter a topic name.')
        else:
            create_topic(st.session_state.user_id, title.strip(), description.strip(), status)
            st.session_state.topic_form_version += 1  # fresh widget keys clear every input
            st.success('Topic added successfully!')
            st.rerun()

    st.divider()
    st.subheader('Manage topics')
    for topic in get_topics(st.session_state.user_id):
        with st.expander(f"{topic['title']} · {topic['status']}"):
            with st.form(f"edit_topic_form_{topic['id']}"):
                new_title = st.text_input('Topic name', value=topic['title'], key=f"topic_title_{topic['id']}")
                new_description = st.text_area('Description', value=topic['description'], key=f"topic_desc_{topic['id']}")
                choices = ['Not started', 'In progress', 'Completed']
                new_status = st.selectbox('Status', choices, index=choices.index(topic['status']), key=f"topic_status_{topic['id']}")
                update = st.form_submit_button('Save changes')
            if update:
                if not new_title.strip():
                    st.error('Topic name cannot be empty.')
                else:
                    edit_topic(st.session_state.user_id, topic['id'], new_title.strip(), new_description.strip(), new_status)
                    st.success('Topic updated successfully.')
                    st.rerun()
            confirm_key = f"confirm_topic_delete_{topic['id']}"
            if st.button('Delete topic', key=f"delete_topic_{topic['id']}"):
                st.session_state[confirm_key] = True
            if st.session_state.get(confirm_key):
                st.warning('Delete this topic? Existing journal entries will be kept but unlinked from this topic.')
                yes, no = st.columns(2)
                if yes.button('Confirm delete', key=f"yes_topic_{topic['id']}", type='primary'):
                    remove_topic(st.session_state.user_id, topic['id'])
                    st.session_state[confirm_key] = False
                    st.success('Topic deleted.')
                    st.rerun()
                if no.button('Cancel', key=f"no_topic_{topic['id']}"):
                    st.session_state[confirm_key] = False
                    st.rerun()


def journal_page():
    st.title('Learning Journal')
    st.write('Create a new learning note, or edit an existing note to update it.')
    user_id = st.session_state.user_id
    topics = get_topics(user_id)
    topic_map = {topic['title']: topic['id'] for topic in topics}
    edit_id = st.session_state.editing_journal_id
    entries = get_journal(user_id)
    current = next((entry for entry in entries if entry['id'] == edit_id), None) if edit_id else None
    version = st.session_state.journal_form_version
    if current:
        st.subheader('Edit journal entry')
        initial_title, initial_content = current['title'], current['content']
        initial_topic = next((name for name, tid in topic_map.items() if tid == current['topic_id']), 'No topic')
    else:
        st.subheader('New journal entry')
        initial_title, initial_content, initial_topic = '', '', 'No topic'
    topic_choices = ['No topic'] + list(topic_map.keys())
    with st.form(f'journal_form_{version}'):
        title = st.text_input('Entry title', value=initial_title, key=f'journal_title_{version}')
        selected_topic = st.selectbox('Related topic (optional)', topic_choices,
                                      index=topic_choices.index(initial_topic), key=f'journal_topic_{version}')
        content = st.text_area('What did you learn?', value=initial_content, height=170,
                               key=f'journal_content_{version}')
        submitted = st.form_submit_button('Update entry' if current else 'Create entry', use_container_width=True)
    if submitted:
        if not title.strip() or not content.strip():
            st.error('Please fill in both the entry title and learning notes.')
        else:
            topic_id = topic_map.get(selected_topic)
            save_journal(user_id, title.strip(), content.strip(), topic_id, edit_id)
            st.success('Learning journal entry updated successfully.' if edit_id else 'Learning journal entry created successfully.')
            st.session_state.editing_journal_id = None
            st.session_state.journal_form_version += 1
            st.rerun()
    if current and st.button('Cancel editing'):
        st.session_state.editing_journal_id = None
        st.session_state.journal_form_version += 1
        st.rerun()

    st.divider()
    st.subheader('Saved learning items')
    entries = get_journal(user_id)
    if not entries:
        st.info('Your learning journal is empty. Create your first entry above.')
    for entry in entries:
        related = entry['topic_title'] or 'General'
        with st.expander(f"{entry['title']} · {related} · Updated {entry['updated_at']}"):
            st.write(entry['content'])
            edit_col, delete_col = st.columns(2)
            if edit_col.button('Edit entry', key=f"edit_entry_{entry['id']}"):
                st.session_state.editing_journal_id = entry['id']
                st.session_state.journal_form_version += 1
                st.rerun()
            confirm_key = f"confirm_journal_delete_{entry['id']}"
            if delete_col.button('Delete entry', key=f"delete_entry_{entry['id']}"):
                st.session_state[confirm_key] = True
            if st.session_state.get(confirm_key):
                st.warning('Permanently delete this learning journal item?')
                yes, no = st.columns(2)
                if yes.button('Confirm delete', key=f"yes_entry_{entry['id']}", type='primary'):
                    remove_journal(user_id, entry['id'])
                    st.session_state[confirm_key] = False
                    if st.session_state.editing_journal_id == entry['id']:
                        st.session_state.editing_journal_id = None
                    st.success('Learning item deleted.')
                    st.rerun()
                if no.button('Cancel', key=f"no_entry_{entry['id']}"):
                    st.session_state[confirm_key] = False
                    st.rerun()


def tutor_page():
    st.title('AI Python Tutor')
    st.caption('Ask a question. The tutor can tailor explanations using your topics and recent journal entries.')
    if not os.getenv('OPENAI_API_KEY'):
        st.info('AI tutor is optional. Set OPENAI_API_KEY in your environment to enable AI answers; other features work without it.')
    for message in st.session_state.tutor_messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
    question = st.chat_input('Ask a beginner Python question...')
    if question:
        st.session_state.tutor_messages.append({'role': 'user', 'content': question})
        with st.chat_message('user'):
            st.markdown(question)
        with st.chat_message('assistant'):
            with st.spinner('Preparing an explanation...'):
                try:
                    answer = ask_tutor(st.session_state.user_id, question)
                except Exception as error:
                    answer = f'The tutor could not respond. Please check your API key and connection. ({error})'
                st.markdown(answer)
        st.session_state.tutor_messages.append({'role': 'assistant', 'content': answer})


if st.session_state.user_id is None:
    show_auth()
else:
    selected_page = sidebar()
    if selected_page == 'Dashboard':
        dashboard()
    elif selected_page == 'My Topics':
        topics_page()
    elif selected_page == 'Learning Journal':
        journal_page()
    else:
        tutor_page()
