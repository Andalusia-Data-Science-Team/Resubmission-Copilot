import operator
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import (AIMessage, AnyMessage, HumanMessage,
                                     SystemMessage)
from langchain_fireworks import ChatFireworks
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph

from src.resubmission.prompt import chatbot_prompt, justification_prompt

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


class InsuranceAgent:
    def __init__(
        self,
        model="accounts/fireworks/models/gpt-oss-120b",
        message_window=7,
    ):
        self.llm = ChatFireworks(
            model=model,
            temperature=0.2,
            max_tokens=10000,
            model_kwargs={"stream": True},  # Using stream to escape Fireworks error "Requests with max_tokens > 4096 must have stream=true"
            request_timeout=(120, 120),
        )
        self.message_window = message_window

        graph = StateGraph(AgentState)
        graph.add_node("llm", self._call_llm)
        graph.set_entry_point("llm")
        graph.add_edge("llm", END)

        self.memory = InMemorySaver()
        self.graph = graph.compile(checkpointer=self.memory)

    def _call_llm(self, state: AgentState):
        context = state["messages"][:3]
        convo = state["messages"][3:]

        if len(convo) >= self.message_window:
            convo = convo[-self.message_window:]
            # This modifies the state for THIS execution
            messages_to_use = context + convo
        else:
            messages_to_use = state["messages"]

        response = self.llm.invoke(messages_to_use)

        # Return ONLY the new message to append
        return {"messages": [response]}

    def respond(self, user_input: str, thread_id: str, policy: str, visit_info: str):
        thread = {"configurable": {"thread_id": thread_id}}

        # Check if this is the first input message in the thread
        try:
            messages = self.graph.get_state(thread).values.get("messages", [])
            human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
            is_first_call = len(human_msgs) == 0
        except Exception:
            is_first_call = True

        # Only add system context on FIRST call
        if is_first_call:
            state = {
                "messages": [
                    SystemMessage(content=policy),
                    SystemMessage(content=chatbot_prompt),
                    SystemMessage(
                        content="Patient's info and services provided during the visit: " + visit_info
                    ),
                    HumanMessage(content=user_input),
                ]
            }
        else:
            print(list(self.graph.get_state_history(thread)))
            # Subsequent calls: only add the new user message
            state = {
                "messages": [HumanMessage(content=user_input)]
            }

        full_response = ""
        for chunk, metadata in self.graph.stream(
            state, thread, version="v1", stream_mode="messages"
        ):
            if chunk.content:
                full_response += chunk.content

        checkpoint = self.graph.get_state(thread)
        full_state = checkpoint.values
        messages = full_state.get("messages", [])
        print("\n=== MESSAGE HISTORY ===")
        for i, msg in enumerate(messages):
            role = msg.__class__.__name__  # SystemMessage, HumanMessage, AIMessage
            print(f"\n[{i+1}] {role}")
            print(msg.content)

        return full_response

    def justify(self, thread_id: str, policy: str, claim_info: str):
        thread = {"configurable": {"thread_id": thread_id}}

        chat_model = ChatFireworks(
            model="accounts/fireworks/models/deepseek-v3p1",
            temperature=0.2,
            max_tokens=4000,
        )
        context = [
            SystemMessage(content=justification_prompt),
            SystemMessage(content=policy),
            SystemMessage(content=str(claim_info)),
        ]
        response = chat_model.invoke(context).content
        self.graph.update_state(
            thread,
            {
                "messages": [
                    SystemMessage(
                        content="Justification generated for rejected service"
                    ),
                    AIMessage(content=response),
                ]
            },
        )
        return response


_agent = InsuranceAgent()


def get_agent_response(
    user_input,
    thread_id,
    policy="",
    visit_info="",
):
    """
    Call this inside your Flask chat route.
    Example:
        answer = get_agent_response(msg, session_id, policy, visit_info)
    """
    if user_input:
        return _agent.respond(
            user_input=user_input,
            thread_id=thread_id,
            policy=policy,
            visit_info=visit_info,
        )
    else:
        return _agent.justify(
            thread_id=thread_id, policy=policy, claim_info=visit_info
        )
