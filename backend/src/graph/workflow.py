from langgraph.graph import StateGraph , END

from backend.src.graph.state import VideoAuditState
from backend.src.graph.nodes import index_video_node , auto_content_node



def create_graph():
    # define the graph
    graph_builder = StateGraph(VideoAuditState)

    # add nodes
    graph_builder.add_node("index_video" , index_video_node)
    graph_builder.add_node("auto_content" , auto_content_node)

    # add edges
    graph_builder.set_entry_point("index_video")
    graph_builder.add_edge("index_video" , "auto_content")
    graph_builder.add_edge("auto_content" , END)

    # compile the graph
    video_audit_graph = graph_builder.compile()

    return video_audit_graph


# expose the runable video_audit_graph 
video_audit_graph = create_graph()
