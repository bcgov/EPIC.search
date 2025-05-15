# SEARCH-API

A Flask-based RAG (Retrieval-Augmented Generation) API service that combines vector search with LLM-powered responses.

## Overview

The Search API provides a bridge between:

1. User queries submitted via REST API
2. External vector search service that retrieves relevant documents
3. LLM integration (currently Ollama) that generates context-aware responses

For detailed documentation, see [DOCUMENTATION.md](./DOCUMENTATION.md).

## Getting Started

### Development Environment

* Install the following:
  * [Python](https://www.python.org/)
  * [Docker](https://www.docker.com/)
  * [Docker-Compose](https://docs.docker.com/compose/install/)
* Install Dependencies
  * Run `make setup` in the root of the project (search-api)
* Configure your environment variables (see below)
* Run the application
  * Run `make run` in the root of the project

## Environment Variables

The development scripts for this application allow customization via an environment file in the root directory called `.env`. See an example of the environment variables that can be overridden in `sample.env`.

Key environment variables include:

* `VECTOR_SEARCH_API_URL`: URL for the external vector search service
* `LLM_MODEL`: Ollama model to use
* `LLM_TEMPERATURE`: Temperature parameter for LLM generation
* `LLM_MAX_TOKENS`: Maximum tokens for LLM response
* `LLM_MAX_CONTEXT_LENGTH`: Maximum context length for LLM

## Commands

### Development

The following commands support various development scenarios and needs.
Before running the following commands run `. venv/bin/activate` to enter into the virtual env.

> `make run`
>
> Runs the python application and runs database migrations.  
Open [http://localhost:5000/api](http://localhost:5000/api) to view it in the browser.
> The page will reload if you make edits.
> You will also see any lint errors in the console.
>
> `make test`
>
> Runs the application unit tests
>
> `make lint`
>
> Lints the application code.

## Debugging in the Editor

### Visual Studio Code

Ensure the latest version of [VS Code](https://code.visualstudio.com) is installed.

The [`launch.json`](.vscode/launch.json) is already configured with a launch task (SEARCH-API Launch) that allows you to launch chrome in a debugging capacity and debug through code within the editor.
