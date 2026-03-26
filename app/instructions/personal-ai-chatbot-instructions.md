
---

## `ai-chatbot-build.md`

```md
# ai-chatbot-build.md

## Feature Overview

This file defines the starting implementation for the **AI chatbot feature** inside the main AI backend platform.

This chatbot is only one feature inside the larger AI server.

Its purpose is to answer questions using my real stored data.
The first use case is a **personal profile chatbot**, but the feature should still follow the platform architecture so it can later support other contexts too.

---

## Main Goal

Build a chatbot API that:
- receives a user message
- determines the proper context
- retrieves relevant internal data
- validates whether the data truly supports an answer
- sends compact context to an external LLM only when supported
- returns a short grounded response

If the data is not supported:
- do not generate a fake answer
- return a short “I do not have enough information” style response

---

## Starting Use Case

The first chatbot context is **personal profile Q&A**.

The chatbot should answer questions about:
- who I am
- my skills
- my projects
- my experience
- my tools
- my development style

Use only my real stored data such as:
- `profile.json`
- `projects.json`

Do not invent missing facts.

---

## Required Chat Flow

The chatbot must follow this exact flow:

1. Receive user message
2. Accept optional context name, default to `profile`
3. Load relevant knowledge source(s)
4. Chunk the data if needed
5. Use semantic retrieval to find top candidate chunks
6. Use reranker validation to score support
7. If support score is too low, return unsupported response
8. If support score is high enough, build a compact prompt
9. Call external LLM with compact context only
10. Return short formatted answer

---

## Required Models

### Model 1: semantic retrieval
Use:
`sentence-transformers/all-MiniLM-L6-v2`

Purpose:
- convert user query into embedding
- compare against local data chunks
- retrieve semantically relevant chunks

### Model 2: support validation
Use:
`cross-encoder/ms-marco-MiniLM-L6-v2`

Purpose:
- rerank retrieved chunks
- measure whether they truly support the question
- stop unsupported questions from going to external LLM

### Final answer generation
Use configurable external LLM provider.

Possible providers:
- OpenAI
- Anthropic
- Gemini

The external LLM is for final response generation only.

---

## Golden Rule

**Store full knowledge locally. Retrieve the relevant slice. Validate it. Send only compact context to the external LLM.**

Do not send full JSON files on every request.

---

## Chatbot Behavior Rules

The chatbot must:
- answer only from supported data
- not guess
- not invent achievements or experience
- stay grounded
- be short and clear
- avoid filler
- avoid long unnecessary explanations

If information is missing:
- say it clearly
- do not force a made-up answer

---

## Response Style Rules

Default answer style:
- 1 to 3 short sentences
- direct
- professional
- clear
- around 60 words or less when possible

The chatbot should sound:
- confident only when supported by data
- honest when data is missing

---

## Token and Cost Rules

Design the chatbot to minimize external LLM cost.

Required rules:
- retrieve only relevant chunks
- rerank before calling external LLM
- send compact context only
- keep prompts short
- keep output token limit low
- keep chat history short
- support configurable `max_output_tokens`

Do not waste tokens on:
- full data dumps
- unnecessary system prompt length
- long answer styles
- irrelevant past history

---

## API Endpoint

Starting route:
- `POST /api/v1/ai/chat`

Also include:
- `GET /api/v1/health`

---

## Suggested Chat Request Shape

```json
{
  "message": "What backend technologies does Patrick use?",
  "context": "profile",
  "session_id": "optional-session-id"
}