from langgraph.graph import StateGraph, END


def build_graph(react_loop):
    graph = StateGraph(dict)

    def step(state):
        res = react_loop.run(state["task_header"])
        state.update(res)
        return state

    graph.add_node("step", step)
    graph.set_entry_point("step")
    graph.add_edge("step", END)
    return graph.compile()
