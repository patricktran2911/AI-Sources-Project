# copilot-instructions.md

## Project Vision

This project is a **main AI backend platform** built in **Python**.

It is not a single chatbot.
It is a **central AI server** that can support many AI projects, many contexts, many APIs, and many frontend or backend apps over time.

This project should be designed as a **scalable AI combination system** where:
- one backend can serve many AI features
- each AI feature can have its own context and rules
- multiple apps can call the same AI server
- new AI projects can be added without rewriting the whole architecture

Examples of future AI features:
- personal profile chatbot
- project Q&A assistant
- summarizer
- recommender
- classifier
- extraction service
- workflow assistant
- app-specific AI tools
- context-aware multi-feature AI APIs

---

## Core Product Goal

Build a reusable Python AI backend that:
- exposes AI APIs for many apps
- supports different AI features
- supports different knowledge contexts
- uses modular architecture
- is easy to extend
- is cost-aware
- avoids hallucination
- can grow into a full AI server platform

---

## Main Architecture Principle

Always build this project as a **platform**, not a one-off feature.

Do not think:
- one prompt
- one chatbot
- one app only
- one hardcoded flow

Think:
- one AI server
- many AI modules
- many contexts
- many providers
- many routes
- many clients
- reusable orchestration

---

## Technical Direction

- Language: **Python**
- API framework: **FastAPI**
- Project type: **standalone AI backend server**
- Deployment target: separate AI server
- Client apps: multiple frontends or backends can call this API
- Final generation: external LLM provider
- Internal lightweight support: local retrieval, reranking, routing, and context preparation
- Data source: local JSON first, then scalable to DB/vector DB later

---

## Required Design Philosophy

The system must be:

- modular
- scalable
- reusable
- provider-agnostic
- context-aware
- API-first
- easy to maintain
- easy to extend later

Avoid:
- giant files
- hardcoded project-specific logic everywhere
- prompt logic mixed into route files
- provider logic scattered across the app
- one service file doing everything

---

## High-Level System Layers

The project should be separated into these layers:

### 1. API Layer
Responsibilities:
- receive requests
- validate inputs
- return structured JSON responses
- keep route handlers thin

### 2. Orchestration Layer
Responsibilities:
- coordinate the whole AI flow
- select context
- choose feature logic
- connect retrieval, validation, prompt building, and provider call

### 3. Feature Service Layer
Responsibilities:
- one service per AI feature
- examples:
  - chat
  - summarize
  - suggest
  - extract
  - classify

### 4. Context Layer
Responsibilities:
- define behavior for each context
- examples:
  - profile context
  - project context
  - portfolio context
  - app-specific context
  - future document context

### 5. Retrieval Layer
Responsibilities:
- find relevant internal data
- support semantic retrieval
- support simple structured retrieval
- be replaceable later with vector DB or better search

### 6. Validation Layer
Responsibilities:
- decide whether retrieved data truly supports the answer
- reduce hallucination
- gate external LLM usage

### 7. Prompt Builder Layer
Responsibilities:
- build compact prompts
- apply context rules
- keep prompts clean and reusable

### 8. Provider Layer
Responsibilities:
- communicate with external LLM providers
- isolate provider-specific code
- support future provider switching

### 9. Repository / Data Layer
Responsibilities:
- load local knowledge
- abstract storage
- support future database migration

### 10. Core Layer
Responsibilities:
- config
- logging
- shared exceptions
- common dependencies

---

## Multi-Feature Requirement

This project must support many AI features over time.

Examples:
- chat
- summarize
- suggestion
- extraction
- classification
- Q&A over personal data
- Q&A over projects
- context-based assistant APIs
- future AI tools

Each feature should:
- have its own service
- have its own request/response models
- optionally use its own context rules
- be independently extendable

Do not force all features into one chatbot design.

---

## Multi-Context Requirement

This project must support multiple contexts.

A context means:
- what knowledge is allowed
- what instruction is used
- how retrieval works
- how validation works
- how the final answer should look
- which token strategy is used

Examples of contexts:
- profile
- projects
- portfolio
- documents
- admin
- community app
- future custom contexts

Design a context registry or context handler system so each context can define:
- system instruction
- retrieval sources
- validation rules
- output style
- token limits
- allowed scope

Do not hardcode all context behavior in one file.

---

## AI Combination Strategy

This project should combine lightweight local intelligence with external LLM generation.

### Recommended combination approach
Use local lightweight components for:
- semantic understanding
- retrieval
- reranking
- support validation
- compact context preparation

Use external LLM only for:
- final answer generation
- rewriting
- natural language formatting
- more advanced reasoning when enough data exists

### Golden rule
**Do not send all raw data to the external LLM.**
Retrieve, validate, and compact first.

---

## Starting AI Stack

For the first strong foundation:

### Local semantic retrieval model
Use:
`sentence-transformers/all-MiniLM-L6-v2`

Purpose:
- understand meaning of user prompt
- retrieve relevant internal data

### Local validation / reranking model
Use:
`cross-encoder/ms-marco-MiniLM-L6-v2`

Purpose:
- rerank candidate chunks
- verify whether data is actually relevant enough to answer

### External generation model
Use a configurable external LLM provider.

Possible providers:
- OpenAI
- Anthropic
- Gemini

Keep the provider layer abstract and replaceable.

---

## API Design Rules

The backend must be API-first.

Use versioned routes such as:
- `/api/v1/health`
- `/api/v1/ai/chat`
- `/api/v1/ai/summarize`
- `/api/v1/ai/suggest`
- `/api/v1/ai/extract`
- `/api/v1/ai/classify`
- `/api/v1/ai/contexts`
- `/api/v1/ai/features`

Rules:
- validate all input with Pydantic
- use clean response formats
- keep route handlers thin
- do not put business logic in routes
- design APIs for many clients, not one frontend only

---

## Request and Response Rules

Prefer predictable JSON response shapes.

Example:
```json
{
  "success": true,
  "data": {
    "result": "response text here"
  },
  "meta": {
    "feature": "chat",
    "context": "profile"
  }
}