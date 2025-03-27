import boto3
import time
import json
from botocore.exceptions import ClientError

agents_runtime_client = boto3.client('bedrock-agent-runtime',
                                     region_name='us-east-1',
                                    )

agent_id = "LMS0QRJENV"
# agent_alias_id = "LAET3PKA7G" #version 2 c3.5
agent_alias_id = "VAMG77RCAX" #version 1 nova
session_id = "test002"
prompt = "保险报销政策是怎么样的"

# 示例聊天历史
sample_history = [
    {"role": "user", "content": "你好，我想了解一下保险政策"},
    {"role": "assistant", "content": "您好！我很乐意帮您了解保险政策。请问您想了解哪方面的保险政策呢？例如健康保险、车险、人寿保险等？"}
]

def convert_messages_to_agent_format(messages):
    """
    Converts message format to Bedrock Agent conversation history format.
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

def invoke_agent(agent_id, agent_alias_id, session_id, prompt, message_history=None):
    """
    Sends a prompt for the agent to process and respond to.

    :param agent_id: The unique identifier of the agent to use.
    :param agent_alias_id: The alias of the agent to use.
    :param session_id: The unique identifier of the session. Use the same value across requests
                       to continue the same conversation.
    :param prompt: The prompt that you want Claude to complete.
    :param message_history: Optional list of previous messages in the conversation.
    :return: Inference response from the model.
    """
    t1 = time.time()

    try:
        # Prepare the request parameters
        request_params = {
            'agentId': agent_id,
            'agentAliasId': agent_alias_id,
            'sessionId': session_id,
            'inputText': prompt,
            'enableTrace':True,
            'streamingConfigurations': {"streamFinalResponse": True}
        }
        
        # Add conversation history if available
        if message_history and len(message_history) > 0:
            session_state = convert_messages_to_agent_format(message_history)
            request_params['sessionState'] = session_state
            print(f"Including conversation history: {json.dumps(session_state, indent=2)}")
            
        # Note: The execution time depends on the foundation model, complexity of the agent,
        # and the length of the prompt. In some cases, it can take up to a minute or more to
        # generate a response.
        response = agents_runtime_client.invoke_agent(**request_params)

        completion = ""
        is_first = False
        for event in response.get("completion"):
            t2 = time.time()
            if 'trace' in event:
                print(f"Trace: {event['trace']['trace']}")
                continue
            elif 'chunk' in event:
                chunk = event["chunk"]
                if not is_first:
                    print(f'First Token Time:{t2-t1}')
                    is_first = True
                completion = completion + chunk["bytes"].decode()
                print(chunk["bytes"].decode(),end="",flush=True)

    except ClientError as e:
        print(f"Couldn't invoke agent. {e}")
        raise

    return completion

# 使用聊天历史调用agent
# invoke_agent(agent_id, agent_alias_id, session_id, prompt, sample_history)

# 不使用聊天历史调用agent
invoke_agent(agent_id, agent_alias_id, session_id, prompt)
