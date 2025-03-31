import streamlit as st
import boto3
import time
import json
from botocore.exceptions import ClientError

# Page configuration
st.set_page_config(
    page_title="Agent Chat Interface",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit_session_{int(time.time())}"

if "enable_trace" not in st.session_state:
    st.session_state.enable_trace = True
    
if "message_history_limit" not in st.session_state:
    st.session_state.message_history_limit = 1

# Sidebar for configuration
st.sidebar.title("Agent Configuration")

# AWS Region selection
region = st.sidebar.text_input("AWS Region", value="us-east-1")

# Agent ID and Alias ID inputs
agent_id = st.sidebar.text_input("Agent ID", value="LMS0QRJENV")
agent_alias_id = st.sidebar.text_input("Agent Alias ID", value="VAMG77RCAX")

# Session ID input
st.session_state.session_id = st.sidebar.text_input("Session ID", value="test001")

# Enable trace toggle
st.session_state.enable_trace = st.sidebar.toggle("Enable Trace", value=st.session_state.enable_trace)

# Message history limit
st.session_state.message_history_limit = st.sidebar.slider("Message History Limit", 
                                                          min_value=0, 
                                                          max_value=10, 
                                                          value=st.session_state.message_history_limit, 
                                                          help="Maximum number of previous messages to include in conversation history")

# Reset conversation button
if st.sidebar.button("Reset Conversation"):
    st.session_state.messages = []
    st.rerun()

# Initialize Bedrock Agent Runtime client
@st.cache_resource
def get_bedrock_client(region):
    return boto3.client('bedrock-agent-runtime', region_name=region)

# Main title
st.title("Agent Chat Interface")

# Function to convert Streamlit messages to Bedrock Agent format
def convert_messages_to_agent_format(messages):
    """
    Converts Streamlit message format to Bedrock Agent conversation history format.
    """
    agent_messages = []
    
    for msg in messages:
        agent_messages.append({
            'content': [
                {
                    'text': msg["content"]
                }
            ],
            'role': msg["role"]
        })
    
    return {
        'conversationHistory': {
            'messages': agent_messages
        }
    }

# Function to invoke agent and stream response
def invoke_agent(agent_id, agent_alias_id, session_id, prompt, message_history=None):
    """
    Sends a prompt for the agent to process and respond to with streaming.
    """
    agents_runtime_client = get_bedrock_client(region)
    
    try:
        # Prepare the request parameters
        request_params = {
            'agentId': agent_id,
            'agentAliasId': agent_alias_id,
            'sessionId': session_id,
            'inputText': prompt,
            'enableTrace': st.session_state.enable_trace,
            'streamingConfigurations': {"streamFinalResponse": True}
        }
        
        # Add conversation history if available
        if message_history and len(message_history) > 0:
            session_state = convert_messages_to_agent_format(message_history)
            request_params['sessionState'] = session_state
            
        # Invoke the agent with the prepared parameters
        response = agents_runtime_client.invoke_agent(**request_params)

        # Create placeholders for the streaming response and trace
        response_placeholder = st.empty()
        trace_container = st.container()
        completion = ""
        start_time = time.time()
        first_token_time = None
        
        for event in response.get("completion"):
            if 'trace' in event and st.session_state.enable_trace:
                trace = event['trace']
                if 'trace' in trace:
                    # Display trace information in JSON format
                    # with trace_container:
                    with st.expander(label='Trace', expanded=False):
                        st.subheader("Trace Information")
                        st.json(trace['trace'])
                        
            if "chunk" not in event:
                continue
            chunk = event["chunk"]
            current_time = time.time()
            if first_token_time is None:
                first_token_time = current_time
                latency = first_token_time - start_time
                st.sidebar.metric("First Token Latency", f"{latency:.2f}s")
            
            completion += chunk["bytes"].decode()
            response_placeholder.markdown(completion)
        
        total_time = time.time() - start_time
        st.sidebar.metric("Total Response Time", f"{total_time:.2f}s")
        
        return completion

    except ClientError as e:
        st.error(f"Error invoking agent: {e}")
        return f"Error: {str(e)}"

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask the agent something..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response with streaming
    with st.chat_message("assistant"):
        # Apply message history limit before passing to the agent
        # Ensure conversation history follows the proper alternating pattern of user/assistant
        limited_message_history = []
        if st.session_state.message_history_limit > 0:
            # Get past messages but exclude the current user message (which was just added)
            past_messages = st.session_state.messages[:-1]
            
            # Ensure we have pairs of messages (user followed by assistant)
            # Start from the most recent and work backwards, ensuring we include complete pairs
            pairs_to_include = min(st.session_state.message_history_limit // 2, len(past_messages) // 2)
            
            if pairs_to_include > 0:
                # Get the most recent pairs, starting from the end
                start_idx = len(past_messages) - (pairs_to_include * 2)
                limited_message_history = past_messages[start_idx:]
                
                # Double-check that our history starts with user and alternates properly
                if limited_message_history and limited_message_history[0]["role"] != "user":
                    limited_message_history = limited_message_history[1:]  # Skip the first assistant message
        
        response = invoke_agent(
            agent_id=agent_id,
            agent_alias_id=agent_alias_id,
            session_id=st.session_state.session_id,
            prompt=prompt,
            message_history=limited_message_history
        )
        
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Display usage instructions
st.sidebar.markdown("---")
st.sidebar.subheader("Usage Instructions")
st.sidebar.markdown("""
1. Configure your agent settings in the sidebar
2. Type your message in the chat input
3. View the streaming response from the agent
4. The conversation history is maintained until you reset it
""")

# Display metrics and debug info
st.sidebar.markdown("---")
st.sidebar.subheader("Debug Info")
st.sidebar.markdown(f"Total Messages: {len(st.session_state.messages)}")
st.sidebar.markdown(f"Messages in History: {min(len(st.session_state.messages)-1, st.session_state.message_history_limit) if len(st.session_state.messages) > 0 else 0} (Limit: {st.session_state.message_history_limit})")
st.sidebar.markdown(f"Trace Enabled: {'Yes' if st.session_state.enable_trace else 'No'}")
