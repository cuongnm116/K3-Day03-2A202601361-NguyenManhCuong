# ReAct Agent Flowchart

```mermaid
flowchart TD
    U["User query"] --> P["Build prompt with history"]
    P --> L["LLM Provider"]
    L --> D{"Parse response"}
    D -->|Final Answer| E["Return grounded answer"]
    D -->|Valid Action| R{"Tool in registry?"}
    D -->|Malformed output| O1["Append structured error Observation"]
    R -->|No| O2["Append unknown_tool Observation"]
    R -->|Yes| V2{"Repeated Action in V2?"}
    V2 -->|Yes| O3["Append repeated_action Observation"]
    V2 -->|No| T["Execute exactly one tool"]
    T --> O4["Append tool result Observation"]
    O1 --> B{"Steps remaining?"}
    O2 --> B
    O3 --> B
    O4 --> B
    B -->|Yes| P
    B -->|No| F["Safe fallback"]
```

Available tool registry:

```text
check_stock → get product price, stock, status, and unit weight
get_discount → validate coupon and return discount percentage
calc_shipping → calculate shipping cost and estimated delivery days
```
