from dotenv import load_dotenv
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_fireworks import ChatFireworks
from src.resubmission.prompt import chatbot_prompt
load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    policy: str
    visit_info: str
    chatbot_prompt: str


class MedicalChatAgent:
    def __init__(
        self,
        model="accounts/fireworks/models/gpt-oss-120b",
        message_window=20,
    ):
        self.llm = ChatFireworks(model=model, temperature=0.2, max_tokens=10000, model_kwargs={"stream": True}, request_timeout=(120, 120))
        self.message_window = message_window

        graph = StateGraph(AgentState)
        graph.add_node("llm", self._call_llm)
        graph.set_entry_point("llm")
        graph.add_edge("llm", END)

        self.memory = InMemorySaver()
        self.graph = graph.compile(checkpointer=self.memory)

    def _call_llm(self, state: AgentState):
        # System + context
        messages = [
            SystemMessage(content=state["chatbot_prompt"]),
            SystemMessage(content=state["policy"]),
            SystemMessage(
                content="For your context, these are the services provided during the visit. Reference them if needed."
            ),
            SystemMessage(content=state["visit_info"]),
        ]

        # Add conversation window
        convo = state["messages"]
        if len(convo) > self.message_window:
            convo = convo[-self.message_window:]
        messages.extend(convo)

        # Model call
        response = self.llm.invoke(messages)
        return {"messages": [response]}

    def respond(
        self,
        user_input: str,
        thread_id: str,
        policy: str,
        visit_info: str
    ):
        thread = {"configurable": {"thread_id": thread_id}}
        state = {
            "messages": [HumanMessage(content=user_input)],
            "policy": policy,
            "visit_info": visit_info,
            "chatbot_prompt": chatbot_prompt,
        }

        full_response = ""
        for chunk, metadata in self.graph.stream(state, thread, version="v1", stream_mode="messages"):
            if chunk.content:
                full_response += chunk.content

        # checkpoint = self.graph.get_state(thread)
        # full_conversation = checkpoint.values
        # print(f"\nTotal messages in history: {len(full_conversation['messages'])}")
        # print("\n=== MESSAGES ===")
        # for i, msg in enumerate(full_conversation['messages']):
        #     role = type(msg).__name__  # HumanMessage, AIMessage, etc.
        #     content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        #     print(f"{i+1}. {role}: {content}")
        return full_response


_agent = MedicalChatAgent()


def get_medical_chat_response(
    user_input,
    thread_id,
    policy="",
    visit_info=""
):
    """
    Call this inside your Flask chat route.
    Example:
        answer = get_medical_chat_response(msg, session_id, policy, visit_info)
    """
    return _agent.respond(
        user_input=user_input,
        thread_id=thread_id,
        policy=policy,
        visit_info=visit_info
    )
