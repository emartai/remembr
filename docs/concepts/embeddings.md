# Embeddings

Embeddings power semantic and hybrid retrieval. In the default Docker setup, Remembr uses Ollama with `nomic-embed-text`.

## Lifecycle

1. `POST /memory` stores the episode immediately.
2. The response includes `embedding_status`.
3. A worker generates embeddings asynchronously.
4. Semantic and hybrid retrieval improve once the status becomes `ready`.

## Why `pending` matters

If you store and search in the same request cycle, a just-stored episode may not appear in semantic results yet. Keyword search can still surface it if the text matches.

## Providers

- Ollama by default for local and self-hosted setups
- Other providers can be configured at deployment time

## Experimental Nomic search prefixes

With the Ollama provider, `OLLAMA_TASK_MODE=nomic_search` adds
`search_document: ` to stored text and `search_query: ` to search queries, as
specified in the [Nomic model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5).
Use this mode with a Nomic model trained for these prefixes. It is opt-in;
`legacy` remains the default and sends the original text unchanged.

Set the same mode on the API and every embedding worker. The prefixed mode
records a separate vector identity ending in `|nomic-search-v1`; semantic
search does not compare it with historical raw vectors. Use a fresh space for
experiments. An existing deployment needs its memories re-embedded in the new
mode before semantic retrieval can use them. Changing this setting does not
automatically rebuild vectors. Switching back to `legacy` likewise does not
convert vectors created in the prefixed mode.

This setting is being evaluated with the local benchmark harness. Pilot
supporting-evidence recall is separate from answer accuracy and does not
establish a competitor ranking.

