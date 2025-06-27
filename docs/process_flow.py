from graphviz import Digraph

# --- 1. Create the main graph object ---
dot = Digraph(
    comment="Zenfi AI Condensed Process Flow",
    format="png",
    graph_attr={
        "rankdir": "TB",  # Top-to-Bottom is better for simpler flows
        "splines": "spline",  # Smoother lines for a cleaner look
        "bgcolor": "#ffffff",
        "label": "Zenfi AI - High-Level Process Flow",
        "labelloc": "t",
        "fontsize": "20",
        "fontname": "Helvetica, Arial, sans-serif",
    },
    node_attr={
        "style": "filled,rounded",
        "fontname": "Helvetica, Arial, sans-serif",
        "fontsize": "10",
        "shape": "box",
    },
    edge_attr={
        "fontname": "Helvetica, Arial, sans-serif",
        "fontsize": "9",
        "color": "#333333",
    },
)

# --- 2. Define Node Styles ---
user_action_style = {"shape": "oval", "fillcolor": "#e6f7ff", "color": "#007acc"}
gateway_style = {"shape": "box", "fillcolor": "#e6ffe6", "color": "#00994d"}
decision_style = {
    "shape": "diamond",
    "fillcolor": "#fffacd",
    "color": "#e6b800",
    "width": "2",
    "height": "1",
}
ai_core_style = {"shape": "Mdiamond", "fillcolor": "#fff0e6", "color": "#ff6600"}
data_style = {"shape": "cylinder", "fillcolor": "#f2e6ff", "color": "#8000ff"}
output_style = {"shape": "ellipse", "fillcolor": "#d4edda", "color": "#155724"}

# --- 3. Define the Process Flow Nodes ---

# Start Node
dot.node("start", "User Submits Query\n(via Frontend)", **user_action_style)

# Backend Gateway
dot.node("be_gateway", "FastAPI Gateway\n(Auth & Routing)", **gateway_style)

# Main Decision Point
dot.node("decision_deep_search", "Deep Research\nEnabled?", **decision_style)

# --- Flow 1: Quick Search (ChatService) ---
with dot.subgraph(name="cluster_quick_search") as qs:
    qs.attr(
        label="Quick Search Flow", style="filled", color="#e6f7ff", bgcolor="#f5fcff"
    )
    qs.node(
        "ai_process_query",
        "1. Process & Enrich Query\n(Check KB, Portfolio, Web)",
        **ai_core_style,
    )
    qs.node("ai_tool_loop", "2. Generate Response\n(LLM + Tools Loop)", **ai_core_style)
    qs.node("qs_output", "Stream Chat Response", **output_style)

# --- Flow 2: Deep Search (DeepSearchService) ---
with dot.subgraph(name="cluster_deep_search") as ds:
    ds.attr(
        label="Deep Search Flow", style="filled", color="#fff5e6", bgcolor="#fffaf0"
    )
    ds.node("ai_plan_report", "1. Plan & Research Report Sections", **ai_core_style)
    ds.node("ai_compile_report", "2. Compile Final Report", **ai_core_style)
    ds.node("ds_output", "Return Full Report", **output_style)

# Data Stores (abstracted)
dot.node("data_stores", "Data Stores\n(Postgres, BigQuery, Redis)", **data_style)

# --- 4. Connect the Nodes with Edges ---

dot.edge("start", "be_gateway")
dot.edge("be_gateway", "decision_deep_search")

# Branching from the main decision
dot.edge("decision_deep_search", "ai_process_query", xlabel="No")
dot.edge("decision_deep_search", "ai_plan_report", xlabel="Yes")

# Quick Search Flow
dot.edge("ai_process_query", "data_stores", label="Fetch Context")
dot.edge("data_stores", "ai_tool_loop")
dot.edge("ai_process_query", "ai_tool_loop")
dot.edge("ai_tool_loop", "qs_output")

# Deep Search Flow
dot.edge("ai_plan_report", "ai_compile_report")
dot.edge("ai_compile_report", "ds_output")


# --- 5. Render the graph ---
output_filename = "zenfi_ai_process_flow_condensed"
dot.render(output_filename, view=False)

print(f"Condensed process flow diagram saved as {output_filename}.png")
